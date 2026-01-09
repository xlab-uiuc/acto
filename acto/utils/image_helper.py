import hashlib
import os
import subprocess

from filelock import FileLock


class ImageHelper:
    """Helper class for managing Docker images, including pulling and archiving them."""

    image_archive_prefix = os.path.join(os.getcwd(), ".acto_images")
    image_tool = os.getenv("IMAGE_TOOL", "docker")

    @staticmethod
    def prepare_image_archive(images: list) -> str:
        """
        Prepare an archive of images for testing.

        Args:
            images (list[str]): List of image file paths to include in the archive.

        Returns:
            str: Path to the created archive.
        """

        filename = hashlib.sha256("".join(sorted(images)).encode("utf-8")).hexdigest()

        archive_name = f"{filename}.tar"
        archive_path = os.path.join(ImageHelper.image_archive_prefix, archive_name)

        lock = FileLock(f"{archive_path}.lock")
        with lock:
            if os.path.exists(archive_path):
                return archive_path

            for image in images:
                subprocess.run(
                    [ImageHelper.image_tool, "pull", image],
                    stdout=subprocess.DEVNULL,
                    check=True,
                )
            os.makedirs(ImageHelper.image_archive_prefix, exist_ok=True)
            subprocess.run(
                [ImageHelper.image_tool, "image", "save", "-o", archive_path]
                + list(images),
                stdout=subprocess.DEVNULL,
                check=True,
            )

        return archive_path
