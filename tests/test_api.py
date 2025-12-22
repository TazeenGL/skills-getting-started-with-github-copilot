"""
Test suite for the High School Management System API

Tests cover:
- Retrieving activities
- Signing up for activities
- Unregistering from activities
- Error handling
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app, activities
import copy


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    # Store original state
    original_activities = copy.deepcopy(activities)
    
    yield
    
    # Restore original state after test
    activities.clear()
    activities.update(original_activities)


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects_to_static(self, client):
        """Test that root redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_all_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) == 9  # Should have 9 activities
    
    def test_activity_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_new_participant(self, client):
        """Test signing up a new participant"""
        response = client.post(
            "/activities/Chess%20Club/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
        
        # Verify participant was added
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_participant(self, client):
        """Test that signing up the same participant twice fails"""
        email = "duplicate@mergington.edu"
        
        # First signup should succeed
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signing up for a non-existent activity"""
        response = client.post(
            "/activities/Fake%20Club/signup?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_signup_multiple_activities(self, client):
        """Test that a student can sign up for multiple activities"""
        email = "multi@mergington.edu"
        
        response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert response1.status_code == 200
        
        response2 = client.post(f"/activities/Programming%20Class/signup?email={email}")
        assert response2.status_code == 200
        
        assert email in activities["Chess Club"]["participants"]
        assert email in activities["Programming Class"]["participants"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_existing_participant(self, client):
        """Test unregistering an existing participant"""
        # First sign up
        email = "temp@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={email}")
        
        # Then unregister
        response = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert "Unregistered" in data["message"]
        assert email in data["message"]
        
        # Verify participant was removed
        assert email not in activities["Chess Club"]["participants"]
    
    def test_unregister_non_participant(self, client):
        """Test unregistering someone who isn't signed up"""
        response = client.delete(
            "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregistering from a non-existent activity"""
        response = client.delete(
            "/activities/Fake%20Club/unregister?email=student@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_preserves_other_participants(self, client):
        """Test that unregistering one participant doesn't affect others"""
        # Get initial participants
        initial_participants = activities["Chess Club"]["participants"].copy()
        
        # Add a new participant
        new_email = "newtemp@mergington.edu"
        client.post(f"/activities/Chess%20Club/signup?email={new_email}")
        
        # Unregister the new participant
        client.delete(f"/activities/Chess%20Club/unregister?email={new_email}")
        
        # Verify original participants are still there
        for participant in initial_participants:
            assert participant in activities["Chess Club"]["participants"]
        
        # Verify new participant was removed
        assert new_email not in activities["Chess Club"]["participants"]


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_full_signup_unregister_workflow(self, client):
        """Test complete workflow of signing up and unregistering"""
        email = "workflow@mergington.edu"
        activity = "Programming Class"
        
        # Check initial state
        initial_count = len(activities[activity]["participants"])
        
        # Sign up
        signup_response = client.post(
            f"/activities/{activity.replace(' ', '%20')}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        assert len(activities[activity]["participants"]) == initial_count + 1
        
        # Verify participant is in the list
        assert email in activities[activity]["participants"]
        
        # Get activities and verify
        get_response = client.get("/activities")
        assert get_response.status_code == 200
        assert email in get_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity.replace(' ', '%20')}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        assert len(activities[activity]["participants"]) == initial_count
        
        # Verify participant is removed
        assert email not in activities[activity]["participants"]
    
    def test_activity_capacity_tracking(self, client):
        """Test that activity capacity is properly tracked"""
        response = client.get("/activities")
        data = response.json()
        
        for activity_name, activity_data in data.items():
            current_participants = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            
            # Verify we haven't exceeded capacity
            assert current_participants <= max_participants
            
            # Verify capacity is positive
            assert max_participants > 0
