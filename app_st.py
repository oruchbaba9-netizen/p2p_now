from flask import Flask, request, jsonify
from flask_cors import CORS
from settings_backend import db
from datetime import datetime


app = Flask(__name__)
CORS(app)  # Enable CORS for all routes


@app.route('/api/profile', methods=['GET'])
def get_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        profile = db.get_user_profile(user_id)

        if profile:
            return jsonify({
                'success': True,
                'profile': profile
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Profile not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving profile: {str(e)}'
        }), 500


@app.route('/api/profile/update', methods=['POST'])
def update_profile():
    """Update user profile"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        user_id = data.get('user_id', 1)
        display_name = data.get('display_name')
        status = data.get('status')
        profile_picture = data.get('profile_picture')

        if not display_name or not status:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400

        success = db.update_user_profile(user_id, display_name, status, profile_picture)

        if success:
            return jsonify({
                'success': True,
                'message': 'Profile updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update profile'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }), 500


@app.route('/api/privacy', methods=['GET'])
def get_privacy():
    """Get privacy settings"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        privacy_settings = db.get_privacy_settings(user_id)

        if privacy_settings:
            return jsonify({
                'success': True,
                'privacy': privacy_settings
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Privacy settings not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving privacy settings: {str(e)}'
        }), 500


@app.route('/api/privacy/update', methods=['POST'])
def update_privacy():
    """Update privacy settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        user_id = data.get('user_id', 1)
        last_seen = data.get('last_seen')
        profile_photo = data.get('profile_photo')
        status_visibility = data.get('status_visibility')

        if not all([last_seen, profile_photo, status_visibility]):
            return jsonify({'success': False, 'message': 'Missing privacy settings'}), 400

        success = db.update_privacy_settings(user_id, last_seen, profile_photo, status_visibility)

        if success:
            return jsonify({
                'success': True,
                'message': 'Privacy settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update privacy settings'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating privacy settings: {str(e)}'
        }), 500


@app.route('/api/theme', methods=['GET'])
def get_theme():
    """Get theme settings"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        theme_settings = db.get_theme_settings(user_id)

        if theme_settings:
            return jsonify({
                'success': True,
                'theme': theme_settings
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Theme settings not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving theme settings: {str(e)}'
        }), 500


@app.route('/api/theme/update', methods=['POST'])
def update_theme():
    """Update theme settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        user_id = data.get('user_id', 1)
        theme = data.get('theme')
        chat_wallpaper = data.get('chat_wallpaper')
        wallpaper_color = data.get('wallpaper_color')
        custom_wallpaper = data.get('custom_wallpaper')

        if not all([theme, chat_wallpaper, wallpaper_color]):
            return jsonify({'success': False, 'message': 'Missing theme settings'}), 400

        success = db.update_theme_settings(user_id, theme, chat_wallpaper, wallpaper_color, custom_wallpaper)

        if success:
            return jsonify({
                'success': True,
                'message': 'Theme settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update theme settings'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating theme settings: {str(e)}'
        }), 500


@app.route('/api/notifications', methods=['GET'])
def get_notifications():
    """Get notification settings"""
    try:
        user_id = request.args.get('user_id', 1, type=int)
        notification_settings = db.get_notification_settings(user_id)

        if notification_settings:
            return jsonify({
                'success': True,
                'notifications': notification_settings
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Notification settings not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving notification settings: {str(e)}'
        }), 500


@app.route('/api/notifications/update', methods=['POST'])
def update_notifications():
    """Update notification settings"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400

        user_id = data.get('user_id', 1)
        message_notifications = data.get('message_notifications', False)
        group_notifications = data.get('group_notifications', False)
        two_step_verification = data.get('two_step_verification', False)

        success = db.update_notification_settings(
            user_id,
            int(message_notifications),
            int(group_notifications),
            int(two_step_verification)
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Notification settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to update notification settings'
            }), 400

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error updating notification settings: {str(e)}'
        }), 500


@app.route('/api/settings/all', methods=['GET'])
def get_all_settings():
    """Get all settings for a user"""
    try:
        user_id = request.args.get('user_id', 1, type=int)

        profile = db.get_user_profile(user_id)
        privacy = db.get_privacy_settings(user_id)
        theme = db.get_theme_settings(user_id)
        notifications = db.get_notification_settings(user_id)

        return jsonify({
            'success': True,
            'settings': {
                'profile': profile or {},
                'privacy': privacy or {},
                'theme': theme or {},
                'notifications': notifications or {}
            }
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error retrieving settings: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Settings API is running',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("Starting ok P2P Settings API on port 8001...")
    app.run(debug=True, port=8001, host='0.0.0.0')