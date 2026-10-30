import os

TEST_JWT_SECRET = "test-only-secret-key-for-local-validation-32-bytes"
os.environ["JWT_SECRET_KEY"] = TEST_JWT_SECRET
os.environ["DATABASE_URL"] = "sqlite://"
