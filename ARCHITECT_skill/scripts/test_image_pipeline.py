import unittest

from image_pipeline import extract_image_urls, normalize_url, select_display_images


class ImagePipelineTests(unittest.TestCase):
    def test_normalize_url_drops_tracking_parameters(self):
        self.assertEqual(
            normalize_url("HTTPS://Example.com/a.jpg?utm_source=x&size=large"),
            "https://example.com/a.jpg?size=large",
        )

    def test_extracts_lazy_and_srcset_images_without_ui_assets(self):
        html = '''
        <img data-src="/uploads/a.jpg" />
        <img srcset="/uploads/a.jpg 640w, /uploads/b.webp 1280w" />
        <img src="/assets/logo.png" />
        '''
        self.assertEqual(
            extract_image_urls(html, "https://www.gooood.cn/project.htm"),
            ["https://www.gooood.cn/uploads/a.jpg", "https://www.gooood.cn/uploads/b.webp"],
        )

    def test_selects_exact_and_near_duplicates_once(self):
        items = [
            {"case_slug": "b", "asset_id": "b1", "source_site": "gooood", "image_type": "01_hero",
             "sha256": "same", "phash": "11111111"},
            {"case_slug": "a", "asset_id": "a1", "source_site": "official", "image_type": "01_hero",
             "sha256": "same", "phash": "11111111"},
            {"case_slug": "a", "asset_id": "a2", "source_site": "official", "image_type": "02_site",
             "sha256": "different", "phash": "11111110"},
        ]
        selected = select_display_images(items, phash_threshold=1)
        chosen = [item["asset_id"] for values in selected.values() for item in values]
        self.assertEqual(chosen, ["a2"])


if __name__ == "__main__":
    unittest.main()
