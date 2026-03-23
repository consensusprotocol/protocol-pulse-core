# F-P3-7: Alert History & Precision Tracking — Foundation Document

## Purpose
Full alert log with user-rated precision tracking and analytics.

## Routes
- GET /intelligence/alerts — paginated alert history page
- GET /intelligence/alerts/stats — precision analytics page
- POST /api/intelligence/alerts/<id>/vote — rate alert (correct/false_positive)
- GET /api/intelligence/alerts/precision — precision metrics JSON

## DB Changes
- ALTER TABLE alerts ADD COLUMN user_vote TEXT (correct|false_positive|null)

## Precision Score
- correct / (correct + false_positive) * 100
- Displayed on main terminal Alert Rail and alert stats page
- Minimum sample: displayed from first vote, confidence indicator at 10+
