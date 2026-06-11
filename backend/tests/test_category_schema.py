import unittest

from app.api.v1.categories import to_category_response
from app.models.category import Category
from app.schemas.category import CategoryResponse


class CategorySchemaTest(unittest.TestCase):
    def test_category_response_exposes_video_count(self):
        category = Category(id=1, name="Phone", code="phone", sort_order=0, is_active=True)

        response = to_category_response(category, video_count=3)

        self.assertIsInstance(response, CategoryResponse)
        self.assertEqual(response.video_count, 3)


if __name__ == "__main__":
    unittest.main()
