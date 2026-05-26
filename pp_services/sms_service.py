"""
Sovereign SMS Dispatch Service
High-velocity SMS alerts via GoHighLevel with 98% open rate targeting.
Uses Sarah (The Macro) voice for urgent, brief, high-status messaging.
"""
import os
import logging
import requests
from datetime import datetime
from typing import Dict, Any, List, Optional

logging.basicConfig(level=logging.DEBUG)


class SMSService:
    """Service for sending SMS alerts via GoHighLevel API"""
    
    def __init__(self):
        self.api_key = os.environ.get('GHL_API_KEY')
        self.location_id = os.environ.get('GHL_LOCATION_ID')
        self.base_url = "https://services.leadconnectorhq.com"
        self.initialized = bool(self.api_key and self.location_id)
        
        if self.initialized:
            logging.info("SMS Service initialized with GHL credentials")
        else:
            logging.warning("SMS Service not configured - missing GHL credentials")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get API headers for GHL requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Version": "2021-07-28"
        }
    
    def send_sms(self, contact_id: str, message: str) -> Dict[str, Any]:
        """
        Send an SMS to a specific contact via GHL.
        
        Args:
            contact_id: GHL contact ID
            message: SMS message content (must include STOP keyword)
            
        Returns:
            Dict with success status
        """
        if not self.initialized:
            return {"success": False, "error": "SMS Service not configured"}
        
        if "STOP" not in message:
            message += "\n\nReply STOP to unsubscribe."
        
        try:
            payload = {
                "type": "SMS",
                "contactId": contact_id,
                "message": message
            }
            
            response = requests.post(
                f"{self.base_url}/conversations/messages",
                headers=self._get_headers(),
                json=payload,
                timeout=30
            )
            
            if response.status_code in [200, 201]:
                logging.info(f"SMS sent successfully to contact {contact_id}")
                return {"success": True, "message_id": response.json().get("messageId")}
            else:
                logging.error(f"SMS send failed: {response.status_code} - {response.text}")
                return {"success": False, "error": response.text}
                
        except Exception as e:
            logging.error(f"SMS send error: {e}")
            return {"success": False, "error": str(e)}
    
    def send_bulk_sms(self, tag: str, message: str) -> Dict[str, Any]:
        """
        Send SMS to all contacts with a specific tag.
        
        Args:
            tag: GHL tag to filter contacts (e.g., 'Sovereign_Node', 'Institutional')
            message: SMS message content
            
        Returns:
            Dict with success status and count
        """
        if not self.initialized:
            return {"success": False, "error": "SMS Service not configured"}
        
        try:
            response = requests.get(
                f"{self.base_url}/contacts/",
                headers=self._get_headers(),
                params={
                    "locationId": self.location_id,
                    "query": tag
                },
                timeout=30
            )
            
            if response.status_code != 200:
                return {"success": False, "error": "Failed to fetch contacts"}
            
            contacts = response.json().get("contacts", [])
            sent_count = 0
            errors = []
            
            for contact in contacts:
                contact_id = contact.get("id")
                phone = contact.get("phone")
                
                if contact_id and phone:
                    result = self.send_sms(contact_id, message)
                    if result.get("success"):
                        sent_count += 1
                    else:
                        errors.append({"contact_id": contact_id, "error": result.get("error")})
            
            logging.info(f"Bulk SMS: Sent {sent_count} messages to '{tag}' contacts")
            return {
                "success": True,
                "sent_count": sent_count,
                "total_contacts": len(contacts),
                "errors": errors if errors else None
            }
            
        except Exception as e:
            logging.error(f"Bulk SMS error: {e}")
            return {"success": False, "error": str(e)}
    
    def mega_whale_alert(self, btc_amount: float, source: str, destination: str, 
                          alex_analysis: str) -> Dict[str, Any]:
        """
        Send Mega-Whale Alert SMS (>1,000 BTC) to Sovereign Node and Institutional contacts.
        Uses Sarah (The Macro) voice.
        
        Args:
            btc_amount: Amount of BTC in transaction
            source: Transaction source (e.g., "cold storage", "exchange")
            destination: Transaction destination
            alex_analysis: Alex The Quant's verification/analysis
            
        Returns:
            Dict with dispatch results
        """
        message = f"""🚨 MEGA-WHALE DETECTED: {btc_amount:,.0f} BTC moving from {source} to {destination}. Alex verifies: {alex_analysis}. Sarah says: Get to the terminal now for the Alpha. 🟣 https://protocolpulse.replit.app/whale-watcher

Reply STOP to unsubscribe."""
        
        results = {
            "sovereign_node": self.send_bulk_sms("Sovereign_Node", message),
            "institutional": self.send_bulk_sms("Institutional", message)
        }
        
        total_sent = sum(r.get("sent_count", 0) for r in results.values())
        logging.info(f"MEGA-WHALE ALERT dispatched to {total_sent} operatives")
        
        return {
            "success": True,
            "total_sent": total_sent,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
    
    def satoshi_hour_reminder(self, partner_name: str, drop_time: str, 
                               contact_id: str, signal_points: int) -> Dict[str, Any]:
        """
        Send Satoshi Hour Drop Reminder SMS.
        
        Args:
            partner_name: Partner offering the drop (e.g., "Start9")
            drop_time: Time until drop
            contact_id: GHL contact ID
            signal_points: Contact's current Signal Points
            
        Returns:
            Dict with send result
        """
        message = f"""⚡ SATOSHI HOUR: Sarah here. The {partner_name} Drop is live in {drop_time}. You have {signal_points:,} SP. You need 1,000 to claim. Ready your shield. 🟣 https://protocolpulse.replit.app/satoshi-drops

Reply STOP to unsubscribe."""
        
        return self.send_sms(contact_id, message)
    
    def difficulty_adjustment_alert(self, adjustment_pct: float, 
                                      sarah_analysis: str) -> Dict[str, Any]:
        """
        Send Difficulty Adjustment SMS alert.
        
        Args:
            adjustment_pct: Difficulty adjustment percentage (e.g., +3.4 or -2.1)
            sarah_analysis: Sarah's macro analysis
            
        Returns:
            Dict with dispatch results
        """
        sign = "+" if adjustment_pct > 0 else ""
        
        message = f"""🛠️ NETWORK UPDATE: Difficulty retarget confirmed at {sign}{adjustment_pct:.1f}%. Sarah's take: {sarah_analysis}. See the full breakdown. 🟣 https://protocolpulse.replit.app/live

Reply STOP to unsubscribe."""
        
        return self.send_bulk_sms("Protocol_Pulse_Subscriber", message)
    
    def send_test_pulse(self, phone_number: str = None, contact_id: str = None) -> Dict[str, Any]:
        """
        Send a test SMS pulse to verify the system.
        
        Args:
            phone_number: Phone number to send test to (optional)
            contact_id: GHL contact ID (optional, preferred)
            
        Returns:
            Dict with test result
        """
        if not self.initialized:
            return {"success": False, "error": "SMS Service not configured"}
        
        test_message = f"""🟣 SOVEREIGN MODE TEST PULSE

Protocol Pulse Command Deck verification.
Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Your intelligence feed is active. The empire is operational.

Reply STOP to unsubscribe."""
        
        if contact_id:
            return self.send_sms(contact_id, test_message)
        
        if phone_number:
            try:
                create_payload = {
                    "phone": phone_number,
                    "firstName": "Test",
                    "lastName": "Operative",
                    "locationId": self.location_id,
                    "tags": ["SMS_Test"],
                    "source": "Command Deck Test"
                }
                
                response = requests.post(
                    f"{self.base_url}/contacts/",
                    headers=self._get_headers(),
                    json=create_payload,
                    timeout=30
                )
                
                if response.status_code in [200, 201]:
                    new_contact_id = response.json().get("contact", {}).get("id")
                    if new_contact_id:
                        return self.send_sms(new_contact_id, test_message)
                
                return {"success": False, "error": "Failed to create test contact"}
                
            except Exception as e:
                return {"success": False, "error": str(e)}
        
        return {"success": False, "error": "No phone number or contact ID provided"}


sms_service = SMSService()
