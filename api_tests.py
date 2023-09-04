import unittest
from app import app, db, bcrypt
from unittest.mock import patch

class FlaskAppTestCase(unittest.TestCase):

    def setUp(self):
        app.testing = True
        self.client = app.test_client()

        # Mock database setup, storing password as plain text for testing purposes
        self.user_data = {
            'username': 'testuser',
            'password': 'testpassword',  # plain text password for testing
            'email': 'test@example.com',
            'zip_code': '12345'
        }
        db.users.insert_one(self.user_data)

    def tearDown(self):
        db.users.delete_one({'username': 'testuser'})

    def test_register(self):
        new_user_data = {
            'username': 'newtestuser',
            'password': 'newtestpassword',  # plain text password for testing
            'email': 'newtest@example.com',
            'zip_code': '67890'
        }
        response = self.client.post('/register', data=new_user_data, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Register', response.data)

        # Cleanup: remove the newly registered user
        db.users.delete_one({'username': 'newtestuser'})

    @patch('app.bcrypt.check_password_hash')
    def test_login(self, mock_check):
        mock_check.return_value = True

        response = self.client.post('/login', data={
            'username': 'testuser',
            'password': 'testpassword'  # the plain text password
        })
        self.assertEqual(response.status_code, 302)

    
    @patch('app.bcrypt.check_password_hash')
    def test_invalid_login(self, mock_check):
        mock_check.return_value = False

        response = self.client.post('/login', data={
            'username': 'invaliduser',
            'password': 'invalidpassword'  # the plain text password
        })
        self.assertNotEqual(response.status_code, 302)
        self.assertIn(b'Invalid username or password', response.data)  # Assuming this error message appears in the rendered HTML

    def test_index(self):
        response = self.client.get('/')
        self.assertIn(b'You are not logged in.', response.data)

    def test_logout(self):
    # Assuming the user is logged in at this point
        self.client.get('/logout')
        response = self.client.get('/profile')
        self.assertNotEqual(response.status_code, 200) # Expecting a redirect, which is status code 302

    def test_profile_logged_out(self):
        # Assuming the user is not logged in
        response = self.client.get('/profile')
        self.assertNotEqual(response.status_code, 200) # Expecting a redirect to login page

if __name__ == '__main__':
    unittest.main()
