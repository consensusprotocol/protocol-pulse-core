"""
HighLevel (GHL) CRM Integration Service
Handles subscriber management, Custom Value syncing, and automated intelligence briefings
"""
import os
import logging
import requests
from datetime import datetime
from typing import Optional, Dict, Any


class GHLService:
    """Service for integrating with HighLevel (GoHighLevel) CRM API v2"""
    
    def __init__(self):
        self.api_key = os.environ.get('GHL_API_KEY')
        self.location_id = os.environ.get('GHL_LOCATION_ID')
        self.base_url = "https://services.leadconnectorhq.com"
        self.initialized = bool(self.api_key and self.location_id)
        self._custom_value_ids = {}
        
        if self.initialized:
            logging.info("GHL service initialized successfully")
        else:
            logging.warning("GHL service not configured - missing GHL_API_KEY or GHL_LOCATION_ID")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers for GHL requests"""
        if self.api_key and self.api_key.startswith('pit-'):
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
        else:
            return {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Version": "2021-07-28"
            }
    
    def push_to_ghl(self, email: str, name: str = "", tag: str = "Protocol_Pulse_Subscriber") -> Dict[str, Any]:
        """
        Push a new subscriber to HighLevel CRM.
        
        Args:
            email: Subscriber email address
            name: Subscriber name (optional)
            tag: Tag to apply (default: Protocol_Pulse_Subscriber)
            
        Returns:
            Dict with success status and response data
        """
        if not self.initialized:
            logging.warning("GHL service not initialized - skipping push")
            return {"success": False, "error": "GHL not configured"}
        
        try:
            # Split name into first/last if provided
            first_name = ""
            last_name = ""
            if name:
                parts = name.strip().split(" ", 1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else ""
            
            # Build contact payload
            payload = {
                "email": email,
                "firstName": first_name,
                "lastName": last_name,
                "locationId": self.location_id,
                "tags": [tag],
                "source": "Protocol Pulse Website",
                "customFields": [
                    {"key": "subscription_date", "value": datetime.now().isoformat()},
                    {"key": "subscriber_type", "value": "Sovereign Transactor"}
                ]
            }
            
            # Create or update contact
            response = requests.post(
                f"{self.base_url}/contacts/",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                data = response.json()
                logging.info(f"GHL: Successfully pushed contact {email} with tag {tag}")
                return {
                    "success": True,
                    "contact_id": data.get("contact", {}).get("id"),
                    "message": "Contact created/updated in GHL"
                }
            else:
                logging.error(f"GHL API error: {response.status_code} - {response.text}")
                return {
                    "success": False,
                    "error": f"API error: {response.status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logging.error(f"GHL push error: {e}")
            return {"success": False, "error": str(e)}
    
    def add_tag_to_contact(self, contact_id: str, tag: str) -> bool:
        """Add a tag to an existing contact"""
        if not self.initialized:
            return False
        
        try:
            response = requests.post(
                f"{self.base_url}/contacts/{contact_id}/tags",
                headers=self._get_headers(),
                json={"tags": [tag]},
                timeout=30
            )
            return response.status_code in [200, 201]
        except Exception as e:
            logging.error(f"GHL tag error: {e}")
            return False
    
    def send_daily_brief_to_ghl(self, report_html: str, bitcoin_lens_html: str, 
                                 difficulty: str = "146.47 T", fees: str = "3 sat/vB") -> Dict[str, Any]:
        """
        Push the daily intelligence briefing as a campaign draft to GHL.
        
        Args:
            report_html: The Report section HTML
            bitcoin_lens_html: The Bitcoin Lens section HTML
            difficulty: Current network difficulty
            fees: Current fee rate
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            # Build email content with terminal-style header
            email_html = f'''
            <div style="background: #0a0a0a; color: #00ff41; font-family: 'JetBrains Mono', monospace; padding: 20px;">
                <div style="border: 1px solid #00ff41; padding: 15px; margin-bottom: 20px;">
                    <h1 style="color: #ff6600; margin: 0;">PROTOCOL PULSE INTELLIGENCE BRIEFING</h1>
                    <p style="color: #888; margin: 5px 0 0 0;">{datetime.now().strftime('%B %d, %Y')} | DIFFICULTY: {difficulty} | FEES: {fees}</p>
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h2 style="color: #00ff41; border-bottom: 1px solid #333;">THE REPORT</h2>
                    {report_html}
                </div>
                
                <div style="margin-bottom: 30px;">
                    <h2 style="color: #ff6600; border-bottom: 1px solid #333;">THE BITCOIN LENS</h2>
                    {bitcoin_lens_html}
                </div>
                
                <div style="text-align: center; padding: 20px; border-top: 1px solid #333;">
                    <p style="color: #666;">Transmitted via Protocol Pulse | Sovereign Intelligence Network</p>
                </div>
            </div>
            '''
            
            # Create campaign draft in GHL
            campaign_payload = {
                "locationId": self.location_id,
                "name": f"Daily Intel - {datetime.now().strftime('%Y-%m-%d')}",
                "status": "draft",
                "emailSubject": f"INTEL BRIEFING: Difficulty {difficulty} | {datetime.now().strftime('%b %d')}",
                "emailBody": email_html
            }
            
            response = requests.post(
                f"{self.base_url}/campaigns/",
                headers=self._get_headers(),
                json=campaign_payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logging.info("GHL: Daily briefing campaign draft created")
                return {"success": True, "message": "Campaign draft created"}
            else:
                logging.warning(f"GHL campaign creation returned: {response.status_code}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"GHL daily brief error: {e}")
            return {"success": False, "error": str(e)}
    
    def _get_custom_value_info(self, key: str) -> Optional[Dict[str, str]]:
        """
        Get the custom value ID and name for a given key.
        Fetches and caches all custom values if not already cached.
        Returns dict with 'id' and 'name' keys.
        """
        normalized_key = key.lower().replace(' ', '_')
        if normalized_key in self._custom_value_ids:
            return self._custom_value_ids[normalized_key]
        
        try:
            response = requests.get(
                f"{self.base_url}/locations/{self.location_id}/customValues",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                custom_values = data.get('customValues', [])
                for cv in custom_values:
                    cv_name = cv.get('name', '')
                    cv_id = cv.get('id')
                    if cv_id and cv_name:
                        cv_key = cv_name.lower().replace(' ', '_')
                        self._custom_value_ids[cv_key] = {'id': cv_id, 'name': cv_name}
                        self._custom_value_ids[cv_name.lower()] = {'id': cv_id, 'name': cv_name}
                
                logging.info(f"GHL Custom Values cached: {list(self._custom_value_ids.keys())}")
                return self._custom_value_ids.get(normalized_key)
            else:
                logging.error(f"Failed to fetch GHL custom values: {response.status_code}")
                return None
                
        except Exception as e:
            logging.error(f"Error fetching GHL custom values: {e}")
            return None
    
    def update_custom_value(self, key: str, value: str) -> Dict[str, Any]:
        """
        Update a Custom Value in GHL location settings.
        
        Args:
            key: Custom Value key (e.g., 'bitcoin_difficulty', 'network_hashrate', 'daily_intel_briefing')
            value: Value to set
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            logging.warning("GHL service not initialized - skipping custom value update")
            return {"success": False, "error": "GHL not configured"}
        
        try:
            cv_info = self._get_custom_value_info(key)
            
            if not cv_info:
                logging.warning(f"Custom Value '{key}' not found in GHL. Available keys: {list(self._custom_value_ids.keys())}")
                return {"success": False, "error": f"Custom Value '{key}' not found in GHL"}
            
            custom_value_id = cv_info['id']
            custom_value_name = cv_info['name']
            
            payload = {
                "name": custom_value_name,
                "value": value
            }
            
            response = requests.put(
                f"{self.base_url}/locations/{self.location_id}/customValues/{custom_value_id}",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                log_value = f"'{value[:50]}...'" if len(value) > 50 else f"'{value}'"
                logging.info(f"GHL SYNC SUCCESS: Custom Value '{key}' updated to {log_value}")
                return {"success": True, "key": key, "value": value}
            else:
                logging.error(f"GHL Custom Value update failed: {response.status_code} - {response.text}")
                return {"success": False, "error": f"API error: {response.status_code}"}
                
        except Exception as e:
            logging.error(f"GHL Custom Value error: {e}")
            return {"success": False, "error": str(e)}
    
    def sync_network_metrics(self) -> Dict[str, Any]:
        """
        Sync Bitcoin network metrics (Difficulty and Hashrate) to GHL Custom Values.
        Fetches live data from Mempool.space API.
        
        Returns:
            Dict with success status and synced values
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            from services.node_service import NodeService
            
            stats = NodeService.get_network_stats()
            
            difficulty = stats.get('difficulty', '146.47 T')
            hashrate = stats.get('hashrate', '~977 EH/s')
            
            difficulty_result = self.update_custom_value('bitcoin_difficulty', difficulty)
            hashrate_result = self.update_custom_value('network_hashrate', hashrate)
            
            if difficulty_result.get('success') and hashrate_result.get('success'):
                logging.info(f"GHL NETWORK SYNC SUCCESS: Difficulty={difficulty}, Hashrate={hashrate}")
                return {
                    "success": True,
                    "difficulty": difficulty,
                    "hashrate": hashrate,
                    "synced_at": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "difficulty_result": difficulty_result,
                    "hashrate_result": hashrate_result
                }
                
        except Exception as e:
            logging.error(f"GHL network metrics sync error: {e}")
            return {"success": False, "error": str(e)}
    
    def push_daily_intel_briefing(self, article_body: str) -> Dict[str, Any]:
        """
        Push the Daily Intel Briefing (Bitcoin Lens article body) to GHL Custom Value.
        
        Args:
            article_body: Full article body text/HTML from Bitcoin Lens article
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            result = self.update_custom_value('daily_intel_briefing', article_body)
            
            if result.get('success'):
                logging.info("GHL DAILY INTEL BRIEFING SYNC SUCCESS: Article body pushed to Custom Value")
            
            return result
            
        except Exception as e:
            logging.error(f"GHL Daily Intel Briefing push error: {e}")
            return {"success": False, "error": str(e)}


    def send_webhook_test(self, first_name: str = "Test", signal_points: int = 500, 
                           sovereign_segment: str = "Sovereign Node") -> Dict[str, Any]:
        """
        Send a test webhook payload to GHL inbound webhook URL.
        Requires GHL_WEBHOOK_URL environment variable.
        
        Args:
            first_name: Contact first name (maps to {{contact.first_name}})
            signal_points: Contact's Signal Points (maps to {{contact.signal_points}})
            sovereign_segment: Contact's sovereign segment (maps to {{contact.sovereign_segment}})
            
        Returns:
            Dict with success status and response
        """
        webhook_url = os.environ.get('GHL_WEBHOOK_URL')
        
        if not webhook_url:
            logging.warning("GHL_WEBHOOK_URL not configured - using contact creation fallback")
            return self._create_operative_contact(first_name, signal_points, sovereign_segment)
        
        try:
            payload = {
                "contact": {
                    "first_name": first_name,
                    "signal_points": signal_points,
                    "sovereign_segment": sovereign_segment
                },
                "source": "Protocol Pulse Operative Onboarding",
                "timestamp": datetime.now().isoformat(),
                "event": "operative_onboarding_test"
            }
            
            response = requests.post(
                webhook_url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=30
            )
            
            logging.info(f"GHL Inbound Webhook Response: {response.status_code}")
            
            if response.status_code in [200, 201, 202]:
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "payload_sent": payload,
                    "message": "GHL Inbound Webhook received 200 OK",
                    "webhook_url": webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "error": response.text
                }
                
        except Exception as e:
            logging.error(f"GHL Webhook test error: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_operative_contact(self, first_name: str, signal_points: int, 
                                    sovereign_segment: str) -> Dict[str, Any]:
        """
        Fallback: Create operative contact directly in GHL when webhook URL not configured.
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            response = requests.post(
                f"{self.base_url}/contacts/",
                headers=self._get_headers(),
                json={
                    "firstName": first_name,
                    "locationId": self.location_id,
                    "tags": [f"Segment_{sovereign_segment.replace(' ', '_')}", "Operative", "Protocol_Pulse"],
                    "source": "Protocol Pulse",
                    "customFields": [
                        {"key": "signal_points", "value": str(signal_points)},
                        {"key": "sovereign_segment", "value": sovereign_segment},
                        {"key": "onboarded_at", "value": datetime.now().isoformat()}
                    ]
                },
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                contact_data = response.json()
                return {
                    "success": True,
                    "status_code": response.status_code,
                    "contact_id": contact_data.get("contact", {}).get("id"),
                    "message": "Operative contact created in GHL (webhook fallback)",
                    "note": "Set GHL_WEBHOOK_URL for inbound webhook integration"
                }
            else:
                return {"success": False, "status_code": response.status_code, "error": response.text}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def trigger_sarah_welcome_email(self, contact_id: str) -> Dict[str, Any]:
        """
        Trigger Sarah (The Macro) welcome email for a contact by adding the Sarah_Welcome tag.
        This tag should trigger a GHL workflow that sends the welcome email.
        
        Args:
            contact_id: GHL contact ID
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        workflow_id = os.environ.get('GHL_SARAH_WORKFLOW_ID')
        
        try:
            if workflow_id:
                response = requests.post(
                    f"{self.base_url}/contacts/{contact_id}/workflow/{workflow_id}",
                    headers=self._get_headers(),
                    json={"eventStartTime": datetime.now().isoformat()},
                    timeout=30
                )
                
                if response.status_code in [200, 201, 202]:
                    logging.info(f"Sarah Welcome workflow {workflow_id} triggered for contact {contact_id}")
                    return {"success": True, "message": "Sarah Welcome workflow triggered", "workflow_id": workflow_id}
            
            tag_result = self.add_tag_to_contact(contact_id, "Sarah_Welcome")
            if tag_result:
                logging.info(f"Sarah_Welcome tag added to contact {contact_id} (workflow trigger)")
                return {
                    "success": True, 
                    "message": "Sarah_Welcome tag applied - workflow will trigger automatically",
                    "note": "Set GHL_SARAH_WORKFLOW_ID for direct workflow triggering"
                }
            else:
                return {"success": False, "error": "Failed to add Sarah_Welcome tag"}
                
        except Exception as e:
            logging.error(f"Sarah Welcome trigger error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_sarah_welcome_to_recent_scorecard_users(self) -> Dict[str, Any]:
        """
        Send Sarah Welcome email to all users who completed Sovereign Scorecard in last 24 hours.
        
        Returns:
            Dict with success status and count
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured"}
        
        try:
            response = requests.get(
                f"{self.base_url}/contacts/",
                headers=self._get_headers(),
                params={
                    "locationId": self.location_id,
                    "query": "Scorecard_Complete"
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {"success": False, "error": "Failed to fetch contacts"}
            
            contacts = response.json().get("contacts", [])
            triggered_count = 0
            
            for contact in contacts:
                contact_id = contact.get("id")
                date_added = contact.get("dateAdded")
                
                if contact_id and date_added:
                    try:
                        added_dt = datetime.fromisoformat(date_added.replace('Z', '+00:00'))
                        if (datetime.now(added_dt.tzinfo) - added_dt).total_seconds() < 86400:
                            result = self.trigger_sarah_welcome_email(contact_id)
                            if result.get("success"):
                                triggered_count += 1
                    except Exception as parse_err:
                        logging.warning(f"Date parse error for contact {contact_id}: {parse_err}")
            
            logging.info(f"Sarah Welcome: Triggered {triggered_count} emails to recent Scorecard users")
            return {
                "success": True,
                "triggered_count": triggered_count,
                "total_scorecard_contacts": len(contacts)
            }
            
        except Exception as e:
            logging.error(f"Sarah Welcome batch error: {e}")
            return {"success": False, "error": str(e)}
    
    def verify_api_connection(self) -> Dict[str, Any]:
        """
        Verify GHL API connection is working (expects 200 OK).
        Tests both the API and webhook endpoints if configured.
        
        Returns:
            Dict with connection status
        """
        if not self.initialized:
            return {"success": False, "error": "GHL not configured", "status": "NOT_CONFIGURED"}
        
        results = {
            "api_status": None,
            "webhook_status": None,
            "location_name": None
        }
        
        try:
            response = requests.get(
                f"{self.base_url}/locations/{self.location_id}",
                headers=self._get_headers(),
                timeout=30
            )
            
            if response.status_code == 200:
                location_data = response.json()
                results["api_status"] = "200 OK"
                results["location_name"] = location_data.get("location", {}).get("name", "Unknown")
                logging.info("GHL API connection verified: 200 OK")
            else:
                results["api_status"] = f"Error {response.status_code}"
        except Exception as e:
            results["api_status"] = f"Connection Error: {str(e)}"
        
        webhook_url = os.environ.get('GHL_WEBHOOK_URL')
        if webhook_url:
            try:
                test_response = requests.post(
                    webhook_url,
                    headers={"Content-Type": "application/json"},
                    json={"event": "connection_test", "timestamp": datetime.now().isoformat()},
                    timeout=10
                )
                results["webhook_status"] = f"{test_response.status_code} OK" if test_response.status_code in [200, 201, 202] else f"Error {test_response.status_code}"
            except Exception as webhook_err:
                results["webhook_status"] = f"Not reachable: {str(webhook_err)[:50]}"
        else:
            results["webhook_status"] = "Not configured (GHL_WEBHOOK_URL)"
        
        success = results["api_status"] == "200 OK"
        return {
            "success": success,
            "status_code": 200 if success else 500,
            "status": "CONNECTED" if success else "ERROR",
            "api_status": results["api_status"],
            "webhook_status": results["webhook_status"],
            "location_name": results["location_name"]
        }


# Singleton instance
ghl_service = GHLService()