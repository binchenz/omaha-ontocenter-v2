from app.schemas.error import ErrorResponse


class TestErrorResponse:
    def test_basic_error(self):
        err = ErrorResponse(error="Not Found", detail="Project 42 does not exist")
        assert err.error == "Not Found"
        assert err.detail == "Project 42 does not exist"

    def test_error_without_detail(self):
        err = ErrorResponse(error="Internal Server Error")
        assert err.detail is None

    def test_serialization(self):
        err = ErrorResponse(error="Bad Request", detail="Invalid field")
        data = err.model_dump()
        assert data == {"error": "Bad Request", "detail": "Invalid field"}
