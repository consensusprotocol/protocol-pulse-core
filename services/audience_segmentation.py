"""
Audience Segmentation Engine - K-Means Clustering for Protocol Pulse

Segments users into:
- Sovereign Nodes: Technical users, node operators, self-custody advocates
- Miners: POW-focused, hash rate discussions, difficulty analysis
- Institutional Transactors: Large transactions, treasury management, compliance-aware

Uses Scikit-Learn K-Means clustering based on engagement behavior patterns.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

from app import db
from models import EngagementEvent, ContentPerformance, Article

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AudienceSegment:
    """Represents an audience segment with characteristics."""
    name: str
    description: str
    size: int
    percentage: float
    key_behaviors: List[str]
    preferred_content: List[str]
    engagement_rate: float
    avg_grok_score: float


class AudienceSegmentationEngine:
    """
    K-Means based audience segmentation for Protocol Pulse.
    
    Features used for clustering:
    - Content type engagement (technical vs macro vs sovereignty)
    - Time-of-day activity patterns
    - Engagement depth (views vs replies vs profile visits)
    - Velocity sensitivity (responds in 30-min window?)
    - Strategy responsiveness (which reply strategies work)
    """
    
    SEGMENT_NAMES = {
        0: 'Sovereign Nodes',
        1: 'Miners',
        2: 'Institutional Transactors'
    }
    
    SEGMENT_DESCRIPTIONS = {
        'Sovereign Nodes': 'Technical users focused on self-custody, node operation, and protocol-level understanding. High engagement with technical content.',
        'Miners': 'POW-focused audience interested in hashrate, difficulty, and mining economics. Responds to Ground Truth data.',
        'Institutional Transactors': 'Large-scale Bitcoin holders and treasury managers. Interested in macro analysis, compliance, and institutional adoption.'
    }
    
    SEGMENT_CONTENT_PREFERENCES = {
        'Sovereign Nodes': ['technical', 'on-chain', 'self-custody', 'node', 'UTXO', 'lightning'],
        'Miners': ['hashrate', 'difficulty', 'mining', 'POW', 'energy', 'adjustment'],
        'Institutional Transactors': ['macro', 'treasury', 'institutional', 'regulatory', 'ETF', 'custody']
    }
    
    def __init__(self, n_clusters: int = 3):
        self.n_clusters = n_clusters
        self.kmeans = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.segment_profiles = {}
        self.logger = logging.getLogger(__name__)

    def _extract_user_features(self, days: int = 30) -> Tuple[np.ndarray, List[str]]:
        """
        Extract feature vectors for each unique user/IP hash.
        
        Features:
        - technical_engagement: % of engagement with technical content
        - macro_engagement: % of engagement with macro content
        - sovereignty_engagement: % of engagement with sovereignty content
        - velocity_sensitivity: % of engagements in 30-min window
        - engagement_depth: weighted score of engagement types
        - peak_hour: most active hour (0-23)
        - reply_ratio: replies / total engagements
        - profile_click_ratio: profile visits / total engagements
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        events = EngagementEvent.query.filter(
            EngagementEvent.created_at >= cutoff,
            EngagementEvent.ip_hash.isnot(None)
        ).all()
        
        if not events:
            return np.array([]), []
        
        user_data = {}
        
        for event in events:
            ip_hash = event.ip_hash
            if ip_hash not in user_data:
                user_data[ip_hash] = {
                    'total': 0,
                    'technical': 0,
                    'macro': 0,
                    'sovereignty': 0,
                    'velocity_30min': 0,
                    'replies': 0,
                    'profile_visits': 0,
                    'hours': [],
                    'grok_total': 0,
                    'strategies': {}
                }
            
            ud = user_data[ip_hash]
            ud['total'] += 1
            ud['grok_total'] += event.grok_score_contribution or 0
            
            if event.is_30min_window:
                ud['velocity_30min'] += 1
            
            if event.event_type == 'reply':
                ud['replies'] += 1
            elif event.event_type == 'profile_visit':
                ud['profile_visits'] += 1
            
            ud['hours'].append(event.created_at.hour)
            
            if event.strategy:
                ud['strategies'][event.strategy] = ud['strategies'].get(event.strategy, 0) + 1
            
            content = self._get_content_keywords(event.content_type, event.content_id)
            if content:
                if any(kw in content.lower() for kw in ['technical', 'on-chain', 'utxo', 'protocol', 'node']):
                    ud['technical'] += 1
                if any(kw in content.lower() for kw in ['macro', 'economic', 'monetary', 'policy', 'fiat']):
                    ud['macro'] += 1
                if any(kw in content.lower() for kw in ['sovereign', 'custody', 'freedom', 'censorship']):
                    ud['sovereignty'] += 1
        
        features = []
        user_ids = []
        
        for ip_hash, ud in user_data.items():
            if ud['total'] < 2:
                continue
            
            total = ud['total']
            feature_vector = [
                ud['technical'] / total,
                ud['macro'] / total,
                ud['sovereignty'] / total,
                ud['velocity_30min'] / total,
                ud['grok_total'] / total,
                np.mean(ud['hours']) if ud['hours'] else 12,
                ud['replies'] / total,
                ud['profile_visits'] / total
            ]
            
            features.append(feature_vector)
            user_ids.append(ip_hash)
        
        return np.array(features), user_ids

    def _get_content_keywords(self, content_type: str, content_id: int) -> str:
        """Get content text for keyword analysis."""
        try:
            if content_type == 'article':
                article = Article.query.get(content_id)
                if article:
                    return f"{article.title} {article.category or ''}"
            return ""
        except:
            return ""

    def train(self, days: int = 30) -> Dict:
        """
        Train the K-Means model on user engagement data.
        
        Returns metrics on clustering quality.
        """
        self.logger.info(f"Training audience segmentation on {days} days of data")
        
        features, user_ids = self._extract_user_features(days)
        
        if len(features) < self.n_clusters:
            self.logger.warning(f"Not enough users ({len(features)}) for {self.n_clusters} clusters")
            return {
                'success': False,
                'error': f'Need at least {self.n_clusters} users with 2+ engagements',
                'user_count': len(features)
            }
        
        scaled_features = self.scaler.fit_transform(features)
        
        self.kmeans = KMeans(
            n_clusters=self.n_clusters,
            random_state=42,
            n_init=10,
            max_iter=300
        )
        
        labels = self.kmeans.fit_predict(scaled_features)
        
        silhouette = silhouette_score(scaled_features, labels) if len(set(labels)) > 1 else 0
        
        self._build_segment_profiles(features, labels, user_ids)
        
        self.is_trained = True
        
        return {
            'success': True,
            'n_clusters': self.n_clusters,
            'user_count': len(features),
            'silhouette_score': round(silhouette, 3),
            'segment_sizes': {
                self.SEGMENT_NAMES.get(i, f'Segment {i}'): int(np.sum(labels == i))
                for i in range(self.n_clusters)
            },
            'trained_at': datetime.utcnow().isoformat()
        }

    def _build_segment_profiles(
        self,
        features: np.ndarray,
        labels: np.ndarray,
        user_ids: List[str]
    ):
        """Build detailed profiles for each segment."""
        feature_names = [
            'technical_engagement',
            'macro_engagement', 
            'sovereignty_engagement',
            'velocity_sensitivity',
            'engagement_depth',
            'peak_hour',
            'reply_ratio',
            'profile_click_ratio'
        ]
        
        for cluster_id in range(self.n_clusters):
            cluster_mask = labels == cluster_id
            cluster_features = features[cluster_mask]
            
            if len(cluster_features) == 0:
                continue
            
            avg_features = np.mean(cluster_features, axis=0)
            
            segment_name = self.SEGMENT_NAMES.get(cluster_id, f'Segment {cluster_id}')
            
            if avg_features[0] > avg_features[1] and avg_features[0] > avg_features[2]:
                inferred_name = 'Sovereign Nodes'
            elif avg_features[1] > avg_features[0]:
                inferred_name = 'Institutional Transactors'
            else:
                inferred_name = 'Miners'
            
            key_behaviors = []
            if avg_features[3] > 0.3:
                key_behaviors.append("High velocity responder (active in 30-min window)")
            if avg_features[6] > 0.2:
                key_behaviors.append("Active replier (high conversation engagement)")
            if avg_features[7] > 0.1:
                key_behaviors.append("Profile visitor (curious about sources)")
            if avg_features[5] < 8:
                key_behaviors.append("Early bird (active before 8am UTC)")
            elif avg_features[5] > 20:
                key_behaviors.append("Night owl (active after 8pm UTC)")
            
            self.segment_profiles[cluster_id] = {
                'name': inferred_name,
                'original_name': segment_name,
                'size': int(np.sum(cluster_mask)),
                'percentage': round(np.sum(cluster_mask) / len(labels) * 100, 1),
                'avg_features': {
                    name: round(float(val), 3) 
                    for name, val in zip(feature_names, avg_features)
                },
                'key_behaviors': key_behaviors,
                'preferred_content': self.SEGMENT_CONTENT_PREFERENCES.get(inferred_name, []),
                'user_ids': [user_ids[i] for i, m in enumerate(cluster_mask) if m]
            }

    def predict_segment(self, user_features: List[float]) -> Dict:
        """
        Predict which segment a user belongs to based on their behavior.
        
        Args:
            user_features: [technical, macro, sovereignty, velocity, depth, hour, reply, profile]
        
        Returns:
            Segment info with confidence
        """
        if not self.is_trained:
            return {'error': 'Model not trained', 'segment': 'Unknown'}
        
        try:
            scaled = self.scaler.transform([user_features])
            cluster_id = self.kmeans.predict(scaled)[0]
            
            distances = self.kmeans.transform(scaled)[0]
            confidence = 1 - (distances[cluster_id] / np.sum(distances))
            
            profile = self.segment_profiles.get(cluster_id, {})
            
            return {
                'segment': profile.get('name', f'Segment {cluster_id}'),
                'cluster_id': int(cluster_id),
                'confidence': round(float(confidence), 3),
                'key_behaviors': profile.get('key_behaviors', []),
                'preferred_content': profile.get('preferred_content', [])
            }
            
        except Exception as e:
            self.logger.error(f"Prediction error: {e}")
            return {'error': str(e), 'segment': 'Unknown'}

    def get_segment_summary(self) -> Dict:
        """Get summary of all segments for sponsor reporting."""
        if not self.is_trained:
            return {'error': 'Model not trained', 'segments': []}
        
        segments = []
        total_users = sum(p.get('size', 0) for p in self.segment_profiles.values())
        
        for cluster_id, profile in self.segment_profiles.items():
            segments.append(AudienceSegment(
                name=profile.get('name', f'Segment {cluster_id}'),
                description=self.SEGMENT_DESCRIPTIONS.get(profile.get('name', ''), ''),
                size=profile.get('size', 0),
                percentage=profile.get('percentage', 0),
                key_behaviors=profile.get('key_behaviors', []),
                preferred_content=profile.get('preferred_content', []),
                engagement_rate=profile.get('avg_features', {}).get('reply_ratio', 0) * 100,
                avg_grok_score=profile.get('avg_features', {}).get('engagement_depth', 0)
            ))
        
        return {
            'total_users': total_users,
            'segments': [
                {
                    'name': s.name,
                    'description': s.description,
                    'size': s.size,
                    'percentage': s.percentage,
                    'key_behaviors': s.key_behaviors,
                    'preferred_content': s.preferred_content,
                    'engagement_rate': round(s.engagement_rate, 1),
                    'avg_grok_score': round(s.avg_grok_score, 2)
                }
                for s in sorted(segments, key=lambda x: x.size, reverse=True)
            ],
            'trained_at': datetime.utcnow().isoformat()
        }

    def get_targeting_recommendation(self, topic: str) -> Dict:
        """
        Recommend which segment to target based on topic keywords.
        
        Used by Sarah to personalize launch sequence copy.
        """
        topic_lower = topic.lower()
        
        scores = {
            'Sovereign Nodes': 0,
            'Miners': 0,
            'Institutional Transactors': 0
        }
        
        for segment, keywords in self.SEGMENT_CONTENT_PREFERENCES.items():
            for keyword in keywords:
                if keyword.lower() in topic_lower:
                    scores[segment] += 1
        
        if max(scores.values()) == 0:
            recommended = 'Sovereign Nodes'
            confidence = 0.5
        else:
            recommended = max(scores, key=scores.get)
            total = sum(scores.values())
            confidence = scores[recommended] / total if total > 0 else 0.5
        
        segment_profile = None
        for profile in self.segment_profiles.values():
            if profile.get('name') == recommended:
                segment_profile = profile
                break
        
        return {
            'recommended_segment': recommended,
            'confidence': round(confidence, 2),
            'scores': scores,
            'segment_size': segment_profile.get('size', 0) if segment_profile else 0,
            'segment_percentage': segment_profile.get('percentage', 0) if segment_profile else 0,
            'preferred_content': self.SEGMENT_CONTENT_PREFERENCES.get(recommended, []),
            'copy_guidelines': self._get_copy_guidelines(recommended)
        }

    def _get_copy_guidelines(self, segment: str) -> str:
        """Get copywriting guidelines for targeting a specific segment."""
        guidelines = {
            'Sovereign Nodes': """COPY GUIDELINES FOR SOVEREIGN NODES:
- Lead with technical specifics (block height, UTXO set, mempool)
- Use cypherpunk terminology naturally
- Emphasize self-custody and verification
- End with data that can be independently verified
- Tone: Bloomberg analyst meets OG Bitcoiner""",
            
            'Miners': """COPY GUIDELINES FOR MINERS:
- Lead with POW metrics (hashrate, difficulty adjustment)
- Reference energy economics and mining profitability
- Connect to network security thesis
- Use Ground Truth data from Alex
- Tone: Network operator briefing peers""",
            
            'Institutional Transactors': """COPY GUIDELINES FOR INSTITUTIONAL TRANSACTORS:
- Lead with macro thesis (monetary policy, treasury management)
- Reference institutional adoption milestones
- Connect to regulatory clarity and compliance
- Use Sarah's historical parallels
- Tone: Investment committee memo"""
        }
        
        return guidelines.get(segment, "Use general Bitcoin audience guidelines")


segmentation_engine = AudienceSegmentationEngine()
