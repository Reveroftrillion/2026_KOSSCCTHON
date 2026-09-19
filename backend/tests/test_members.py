"""Membership acceptance checks."""
from backend.tests.test_backend import BackendFixture


class MemberTests(BackendFixture):
    def test_member_flow(self):
        trip = self.create_trip()
        url = f"/api/trips/{trip}/members"
        self.assertEqual(self.client.get(url).json()["data"][0]["user_id"], "owner")
        self.assertEqual(self.client.post(url, json={"user_id": "other"}).status_code, 201)
        self.assertEqual(self.client.post(url, json={"user_id": "other"}).status_code, 409)
        self.assertEqual(len(self.client.get(url).json()["data"]), 2)
        self.assertEqual(self.client.delete(url + "/owner").status_code, 409)
        self.assertEqual(self.client.delete(url + "/other").status_code, 200)
        self.assertEqual(self.client.delete(url + "/other").status_code, 404)

    def test_missing_member_inputs(self):
        trip = self.create_trip()
        self.assertEqual(self.client.post(f"/api/trips/{trip}/members", json={"user_id": "missing"}).status_code, 404)
        self.assertEqual(self.client.get("/api/trips/missing/members").status_code, 404)

    def test_owner_insert_failure_rolls_back_trip(self):
        from sqlalchemy import event, text
        from sqlalchemy.exc import SQLAlchemyError
        def fail(conn, cursor, statement, parameters, context, executemany):
            if "INSERT INTO trip_members" in statement:
                raise SQLAlchemyError("private")
        event.listen(self.engine, "before_cursor_execute", fail)
        try:
            response = self.client.post("/api/trips", json=self.body)
        finally:
            event.remove(self.engine, "before_cursor_execute", fail)
        self.assertEqual(response.status_code, 500)
        with self.engine.connect() as db:
            self.assertEqual(db.execute(text("SELECT COUNT(*) FROM trips")).scalar_one(), 0)
