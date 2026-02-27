"""
Phase 7: CRM Sync Service for HighLevel/GoHighLevel Integration
Syncs user data, operative ranks, and tags to CRM
"""
import os
import logging
import requests
from datetime import datetime

logger = logging.getLogger(__name__)


class CRMSyncService:
    
    RANK_TAGS = {
        1: 'PP_Recruit',
        2: 'PP_Operative',
        3: 'PP_Sovereign_Elite'
    }
    
    def __init__(self):
        self.api_key = os.environ.get('GHL_API_KEY')
        self.location_id = os.environ.get('GHL_LOCATION_ID')
        self.base_url = 'https://rest.gohighlevel.com/v1'
        self.enabled = bool(self.api_key and self.location_id)
        
        if self.enabled:
            logger.info("CRM Sync Service initialized successfully")
        else:
            logger.warning("CRM Sync Service disabled - missing GHL_API_KEY or GHL_LOCATION_ID")
    
    def _get_headers(self):
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def sync_user_to_highpoint(self, user):
        """Sync user data to HighLevel CRM"""
        if not self.enabled:
            logger.warning("CRM sync skipped - service disabled")
            return {'success': False, 'error': 'CRM service disabled'}
        
        try:
            rank_tag = self.RANK_TAGS.get(user.operative_rank, 'PP_Recruit')
            
            tags = [rank_tag, 'Protocol_Pulse_User']
            if user.drill_completions > 0:
                tags.append('PP_Drill_Complete')
            if user.drill_completions >= 5:
                tags.append('PP_Master_Driller')
            if user.brief_clicks >= 10:
                tags.append('PP_Engaged_Reader')
            
            contact_data = {
                'email': user.email,
                'name': user.username,
                'tags': tags,
                'customField': {
                    'operative_rank': user.operative_rank,
                    'drill_completions': user.drill_completions,
                    'brief_clicks': user.brief_clicks,
                    'rank_name': user.get_rank_name(),
                    'last_sync': datetime.utcnow().isoformat()
                }
            }
            
            existing = self._find_contact_by_email(user.email)
            
            if existing:
                result = self._update_contact(existing['id'], contact_data)
            else:
                result = self._create_contact(contact_data)
            
            if result.get('success'):
                from app import db
                user.crm_synced_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"CRM sync successful for user {user.id}: {user.email}")
            
            return result
            
        except Exception as e:
            logger.error(f"CRM sync failed for user {user.id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def _find_contact_by_email(self, email):
        """Find existing contact by email"""
        try:
            url = f"{self.base_url}/contacts/lookup"
            params = {'email': email}
            response = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('contacts'):
                    return data['contacts'][0]
            return None
        except Exception as e:
            logger.error(f"Contact lookup failed: {e}")
            return None
    
    def _create_contact(self, contact_data):
        """Create new contact in CRM"""
        try:
            url = f"{self.base_url}/contacts"
            response = requests.post(url, headers=self._get_headers(), json=contact_data, timeout=10)
            
            if response.status_code in [200, 201]:
                return {'success': True, 'action': 'created', 'data': response.json()}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def _update_contact(self, contact_id, contact_data):
        """Update existing contact in CRM"""
        try:
            url = f"{self.base_url}/contacts/{contact_id}"
            response = requests.put(url, headers=self._get_headers(), json=contact_data, timeout=10)
            
            if response.status_code == 200:
                return {'success': True, 'action': 'updated', 'data': response.json()}
            else:
                return {'success': False, 'error': response.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def batch_sync_users(self, users):
        """Sync multiple users to CRM"""
        results = {'synced': 0, 'failed': 0, 'errors': []}
        
        for user in users:
            result = self.sync_user_to_highpoint(user)
            if result.get('success'):
                results['synced'] += 1
            else:
                results['failed'] += 1
                results['errors'].append({'user_id': user.id, 'error': result.get('error')})
        
        logger.info(f"Batch CRM sync complete: {results['synced']} synced, {results['failed']} failed")
        return results


crm_sync = CRMSyncService()
