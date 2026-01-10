"""
Simple MakerGrid API Test

Tests login and image-to-3D generation with a single Kyur pose.
"""

import asyncio
import aiohttp
import sys
from pathlib import Path


class MakerGridClient:
    """Minimal MakerGrid client for testing."""

    BASE_URL = "https://makergrid.pythonanywhere.com"

    def __init__(self, access_token: str, refresh_token: str = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self._session = None

    async def _get_session(self):
        if self._session is None:
            cookies = {}
            if self.refresh_token:
                cookies["refresh_token"] = self.refresh_token
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.access_token}"},
                cookies=cookies
            )
        return self._session

    @staticmethod
    async def login(username: str, password: str) -> dict:
        """Login to MakerGrid and get access/refresh tokens."""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{MakerGridClient.BASE_URL}/api/accounts/blender/login/",
                data={"username": username, "password": password}
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    raise Exception(f"Login failed ({resp.status}): {error}")
                data = await resp.json()
                return {
                    "access": data.get("access"),
                    "refresh": data.get("refresh"),
                    "user": data.get("user", {})
                }

    async def generate_from_image(self, image_path: Path, prompt: str = "3d model") -> dict:
        """Submit image for 3D generation."""
        session = await self._get_session()

        with open(image_path, "rb") as f:
            image_data = f.read()

        form = aiohttp.FormData()
        form.add_field("image", image_data, filename=image_path.name, content_type="image/png")
        form.add_field("prompt", prompt)  # May be required by newer MakerGrid API

        async with session.post(f"{self.BASE_URL}/api/makers/image-to-model/", data=form) as resp:
            if resp.status != 200 and resp.status != 201:
                error = await resp.text()
                raise Exception(f"Generation request failed ({resp.status}): {error}")
            return await resp.json()

    async def check_status(self, task_id: str) -> dict:
        """Check task status."""
        session = await self._get_session()

        # Send all required fields in JSON body (MakerGrid API requirements)
        payload = {
            "task_id": task_id,
            "prompt": "3d model",
            "style": "realistic",
            "complexity": "medium",
            "optimize_printing": True
        }
        async with session.post(
            f"{self.BASE_URL}/api/makers/check-task-status/{task_id}/",
            json=payload
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise Exception(f"Status check failed ({resp.status}): {error}")
            return await resp.json()

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


async def test_makergrid(username: str, password: str, image_path: Path):
    """Test MakerGrid API with a single image."""

    print("=" * 50)
    print("MAKERGRID API TEST")
    print("=" * 50)

    # Step 1: Login
    print(f"\n[1/4] Logging in as '{username}'...")
    try:
        tokens = await MakerGridClient.login(username, password)
        print(f"      Success! User: {tokens.get('user', {}).get('username', 'unknown')}")
    except Exception as e:
        print(f"      FAILED: {e}")
        return

    # Step 2: Create client
    client = MakerGridClient(tokens["access"], tokens.get("refresh"))

    try:
        # Step 3: Submit image
        print(f"\n[2/4] Submitting image: {image_path.name}")
        result = await client.generate_from_image(image_path)
        print(f"      Response: {result}")

        task_id = result.get("task_id") or result.get("id")
        if not task_id:
            print("      WARNING: No task_id in response, trying to extract...")
            print(f"      Full response: {result}")
            return

        print(f"      Task ID: {task_id}")

        # Step 4: Poll for status
        print(f"\n[3/4] Polling for completion...")
        max_polls = 60  # 5 minutes with 5-second intervals
        for i in range(max_polls):
            await asyncio.sleep(5)
            status = await client.check_status(task_id)
            state = status.get("status") or status.get("state", "unknown")
            progress = status.get("progress", 0)

            bar_len = 20
            filled = int(bar_len * progress / 100) if progress else 0
            bar = "#" * filled + "-" * (bar_len - filled)
            print(f"      [{bar}] {progress:.0f}% - {state}")

            if state in ["completed", "done", "success"]:
                print("\n\n[4/4] Generation complete!")
                print(f"      Model URL: {status.get('model_url') or status.get('output_url')}")
                print(f"      Full response: {status}")
                break
            elif state in ["failed", "error"]:
                print(f"\n\n[4/4] Generation FAILED: {status.get('error', 'Unknown error')}")
                break
        else:
            print("\n\n[4/4] Timeout waiting for generation")

    finally:
        await client.close()

    print("\n" + "=" * 50)


def main():
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Test MakerGrid API")
    parser.add_argument("--username", default=os.getenv("MAKERGRID_USERNAME"), help="MakerGrid username")
    parser.add_argument("--password", default=os.getenv("MAKERGRID_PASSWORD"), help="MakerGrid password")
    parser.add_argument("--image", default=None, help="Image file to use (default: first Kyur pose)")
    args = parser.parse_args()

    if not args.username or not args.password:
        print("ERROR: Username and password required!")
        print("\nUsage: python test_makergrid.py --username USER --password PASS")
        sys.exit(1)

    # Find image
    if args.image:
        image_path = Path(args.image)
    else:
        isolated_dir = Path(__file__).parent / "isolated"
        poses = list(isolated_dir.glob("kyur-*.png"))
        if not poses:
            print("ERROR: No Kyur poses found in isolated/")
            sys.exit(1)
        image_path = sorted(poses)[0]  # Use first pose

    if not image_path.exists():
        print(f"ERROR: Image not found: {image_path}")
        sys.exit(1)

    print(f"Using image: {image_path}")
    asyncio.run(test_makergrid(args.username, args.password, image_path))


if __name__ == "__main__":
    main()
