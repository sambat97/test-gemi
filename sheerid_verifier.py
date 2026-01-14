"""SheerID Student Verification - Main Program"""
import re
import random
import logging
import time
import hashlib
import httpx
from typing import Dict, Optional, Tuple

try:
    from . import config
    from .name_generator import NameGenerator, generate_birth_date
    from .img_generator import generate_image, generate_psu_email
    from .transcript_generator import generate_transcript
except ImportError:
    import config
    from name_generator import NameGenerator, generate_birth_date
    from img_generator import generate_image, generate_psu_email
    from transcript_generator import generate_transcript

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


class SheerIDVerifier:
    """SheerID Student Identity Verifier"""

    def __init__(self, verification_id: str):
        self.verification_id = verification_id
        self.device_fingerprint = self._generate_device_fingerprint()
        self.http_client = httpx.Client(timeout=30.0)

    def __del__(self):
        if hasattr(self, "http_client"):
            self.http_client.close()

    @staticmethod
    def _generate_device_fingerprint() -> str:
        """Generate realistic browser fingerprint to avoid fraud detection"""
        # Realistic screen resolutions
        resolutions = ["1920x1080", "1366x768", "1536x864", "1440x900", "1280x720", "2560x1440"]
        # Common timezones
        timezones = ["-8", "-7", "-6", "-5", "-4", "0", "1", "2", "3", "5.5", "8", "9", "10"]
        # Common languages
        languages = ["en-US", "en-GB", "en-CA", "en-AU", "es-ES", "fr-FR", "de-DE", "pt-BR"]
        # Common platforms
        platforms = ["Win32", "MacIntel", "Linux x86_64"]
        # Browser vendors
        vendors = ["Google Inc.", "Apple Computer, Inc.", ""]
        
        components = [
            str(int(time.time() * 1000)),
            str(random.random()),
            random.choice(resolutions),
            str(random.choice(timezones)),
            random.choice(languages),
            random.choice(platforms),
            random.choice(vendors),
            str(random.randint(1, 16)),  # hardware concurrency (CPU cores)
            str(random.randint(2, 32)),  # device memory GB
            str(random.randint(0, 1)),   # touch support
        ]
        return hashlib.md5("|".join(components).encode()).hexdigest()

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL (keep as is)"""
        return url

    @staticmethod
    def parse_verification_id(url: str) -> Optional[str]:
        match = re.search(r"verificationId=([a-f0-9]+)", url, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    def _sheerid_request(
        self, method: str, url: str, body: Optional[Dict] = None
    ) -> Tuple[Dict, int]:
        """Send SheerID API request"""
        # Add realistic browser headers to avoid fraud detection
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Origin": config.SHEERID_BASE_URL,
            "Referer": f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/?verificationId={self.verification_id}",
            "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        try:
            response = self.http_client.request(
                method=method, url=url, json=body, headers=headers
            )
            try:
                data = response.json()
            except Exception:
                data = response.text
            return data, response.status_code
        except Exception as e:
            logger.error(f"SheerID request failed: {e}")
            raise

    def _upload_to_s3(self, upload_url: str, img_data: bytes) -> bool:
        """Upload PNG to S3"""
        try:
            headers = {"Content-Type": "image/png"}
            response = self.http_client.put(
                upload_url, content=img_data, headers=headers, timeout=60.0
            )
            return 200 <= response.status_code < 300
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return False

    def get_verification_status(self) -> Dict:
        """Get current verification status"""
        try:
            status_url = f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}"
            headers = {
                "Accept": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            response = self.http_client.get(status_url, headers=headers)
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Failed to get status: {response.status_code}")
                return {"currentStep": "unknown"}
        except Exception as e:
            logger.error(f"Error getting verification status: {e}")
            return {"currentStep": "unknown"}

    def verify(
        self,
        first_name: str = None,
        last_name: str = None,
        email: str = None,
        birth_date: str = None,
        school_id: str = None,
    ) -> Dict:
        """Execute verification flow"""
        try:
            # Check current verification status first
            logger.info("📊 Mengecek status verification...")
            current_status = self.get_verification_status()
            current_step = current_status.get("currentStep", "initial")
            
            logger.info(f"📋 Status saat ini: {current_step}")
            logger.info(f"📋 Full status: {current_status}")

            # Handle based on current step
            if current_step == "pending":
                return {
                    "success": True,
                    "pending": True,
                    "message": "Verification sudah disubmit sebelumnya, menunggu review",
                    "verification_id": self.verification_id,
                    "status": current_status,
                }
            
            elif current_step == "success":
                return {
                    "success": True,
                    "pending": False,
                    "message": "✅ Verification sudah berhasil sebelumnya!",
                    "verification_id": self.verification_id,
                    "status": current_status,
                }
            
            elif current_step == "error":
                error_msg = ", ".join(current_status.get("errorIds", ["Unknown error"]))
                return {
                    "success": False,
                    "message": f"Verification error: {error_msg}",
                    "verification_id": self.verification_id,
                    "status": current_status,
                }

            # Prepare student data
            if not first_name or not last_name:
                name = NameGenerator.generate()
                first_name = name["first_name"]
                last_name = name["last_name"]

            school_id = school_id or config.DEFAULT_SCHOOL_ID
            school = config.SCHOOLS[school_id]

            if not email:
                email = generate_psu_email(first_name, last_name)
            if not birth_date:
                birth_date = generate_birth_date()

            logger.info(f"Info Mahasiswa: {first_name} {last_name}")
            logger.info(f"Email: {email}")
            logger.info(f"Universitas: {school['name']}")
            logger.info(f"Tanggal Lahir: {birth_date}")
            logger.info(f"Verification ID: {self.verification_id}")

            # Generate document (70% transcript, 30% Penn State screenshot)
            doc_type = "transcript" if random.random() < 0.7 else "screenshot"
            
            if doc_type == "transcript":
                logger.info("Langkah 1/4: Generate academic transcript...")
                img_data = generate_transcript(first_name, last_name, school['name'], birth_date)
                filename = "transcript.png"
            else:
                logger.info("Langkah 1/4: Generate student ID screenshot...")
                img_data = generate_image(first_name, last_name, school_id)
                filename = "student_card.png"
            
            file_size = len(img_data)
            logger.info(f"✅ Ukuran {doc_type}: {file_size / 1024:.2f}KB")

            # Submit student information (only if needed)
            if current_step in ["collectStudentPersonalInfo", "initial", "unknown"]:
                logger.info("Langkah 2/4: Submit info mahasiswa...")
                step2_body = {
                    "firstName": first_name,
                    "lastName": last_name,
                    "birthDate": birth_date,
                    "email": email,
                    "phoneNumber": "",
                    "organization": {
                        "id": int(school_id),
                        "idExtended": school["idExtended"],
                        "name": school["name"],
                    },
                    "deviceFingerprintHash": self.device_fingerprint,
                    "locale": "en-US",
                    "metadata": {
                        "marketConsentValue": False,
                        "refererUrl": f"{config.SHEERID_BASE_URL}/verify/{config.PROGRAM_ID}/?verificationId={self.verification_id}",
                        "verificationId": self.verification_id,
                        "flags": '{"collect-info-step-email-first":"default","doc-upload-considerations":"default","doc-upload-may24":"default","doc-upload-redesign-use-legacy-message-keys":false,"docUpload-assertion-checklist":"default","font-size":"default","include-cvec-field-france-student":"not-labeled-optional"}',
                        "submissionOptIn": "By submitting the personal information above, I acknowledge that my personal information is being collected under the privacy policy of the business from which I am seeking a discount",
                    },
                }

                step2_data, step2_status = self._sheerid_request(
                    "POST",
                    f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/collectStudentPersonalInfo",
                    step2_body,
                )

                if step2_status != 200:
                    logger.error(f"Response Step 2: {step2_data}")
                    raise Exception(f"Langkah 2 gagal (status {step2_status}): {step2_data}")
                if step2_data.get("currentStep") == "error":
                    error_msg = ", ".join(step2_data.get("errorIds", ["Unknown error"]))
                    logger.error(f"Error IDs: {error_msg}")
                    raise Exception(f"Langkah 2 error: {error_msg}")

                logger.info(f"✅ Langkah 2 selesai: {step2_data.get('currentStep')}")
                logger.info(f"📋 Full response step 2: {step2_data}")
                current_step = step2_data.get("currentStep", current_step)
            else:
                logger.info(f"⏭️ Skip langkah 2 (current step: {current_step})")

            # Skip SSO if needed
            if current_step in ["sso", "collectStudentPersonalInfo"]:
                logger.info("Langkah 3/4: Skip SSO verification...")
                step3_data, _ = self._sheerid_request(
                    "DELETE",
                    f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/sso",
                )
                logger.info(f"✅ Langkah 3 selesai: {step3_data.get('currentStep')}")
                logger.info(f"📋 Full response step 3: {step3_data}")
                current_step = step3_data.get("currentStep", current_step)
            else:
                logger.info(f"⏭️ Skip langkah 3 (current step: {current_step})")

            # Upload document and complete submission
            logger.info("Langkah 4/4: Request dan upload dokumen...")
            step4_body = {
                "files": [
                    {"fileName": filename, "mimeType": "image/png", "fileSize": file_size}
                ]
            }
            step4_data, step4_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/docUpload",
                step4_body,
            )
            
            logger.info(f"📋 Response docUpload: {step4_data}")
            
            if not step4_data.get("documents"):
                raise Exception("Tidak bisa mendapatkan upload URL")

            upload_url = step4_data["documents"][0]["uploadUrl"]
            logger.info("✅ Berhasil mendapat upload URL")
            if not self._upload_to_s3(upload_url, img_data):
                raise Exception("Upload S3 gagal")
            logger.info("✅ Student ID berhasil diupload")

            step6_data, step6_status = self._sheerid_request(
                "POST",
                f"{config.SHEERID_BASE_URL}/rest/v2/verification/{self.verification_id}/step/completeDocUpload",
            )
            logger.info(f"✅ Dokumen selesai disubmit: {step6_data.get('currentStep')}")
            logger.info(f"📋 Full response completeDocUpload: {step6_data}")
            logger.info(f"📋 Status code: {step6_status}")
            final_status = step6_data

            # Return result without polling
            result_message = "Dokumen berhasil disubmit, menunggu review"
            
            # Check if submission was actually successful
            if step6_status != 200:
                logger.error(f"⚠️ completeDocUpload status bukan 200: {step6_status}")
                result_message = f"Submit selesai tapi status {step6_status} - cek manual"
            
            return {
                "success": True,
                "pending": True,
                "message": result_message,
                "verification_id": self.verification_id,
                "redirect_url": final_status.get("redirectUrl"),
                "status": final_status,
                "current_step": final_status.get("currentStep"),
            }

        except Exception as e:
            logger.error(f"❌ Verifikasi gagal: {e}")
            logger.exception("Full error traceback:")
            return {"success": False, "message": str(e), "verification_id": self.verification_id}


def main():
    """主函数 - 命令行界面"""
    import sys

    print("=" * 60)
    print("SheerID 学生身份验证工具 (Python版)")
    print("=" * 60)
    print()

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("请输入 SheerID 验证 URL: ").strip()

    if not url:
        print("❌ 错误: 未提供 URL")
        sys.exit(1)

    verification_id = SheerIDVerifier.parse_verification_id(url)
    if not verification_id:
        print("❌ 错误: 无效的验证 ID 格式")
        sys.exit(1)

    print(f"✅ 解析到验证 ID: {verification_id}")
    print()

    verifier = SheerIDVerifier(verification_id)
    result = verifier.verify()

    print()
    print("=" * 60)
    print("验证结果:")
    print("=" * 60)
    print(f"状态: {'✅ 成功' if result['success'] else '❌ 失败'}")
    print(f"消息: {result['message']}")
    if result.get("redirect_url"):
        print(f"跳转 URL: {result['redirect_url']}")
    print("=" * 60)

    return 0 if result["success"] else 1


if __name__ == "__main__":
    exit(main())
