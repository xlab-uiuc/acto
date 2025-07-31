import os
import subprocess


class ImageHelper:
    image_archive_prefix = os.path.join(os.getcwd(), ".acto_images")
    image_tool = os.getenv("IMAGE_TOOL", "docker")

    @staticmethod
    def prepare_image_archive(images: list[str]) -> str:
        """
        Prepare an archive of images for testing.

        Args:
            images (list[str]): List of image file paths to include in the archive.

        Returns:
            str: Path to the created archive.
        """

        digest = hash("".join(sorted(images)))

        archive_name = f"{digest}.tar"
        archive_path = os.path.join(
            ImageHelper.image_archive_prefix, archive_name
        )

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
