# Bitcoin Live Transaction Visualizer - Game Engine Export

## Overview
This document contains all specifications, logic, and data formats needed to rebuild the Bitcoin live transaction visualizer in Unreal Engine, Unity, or any professional game engine.

---

## CONCEPT: "Sovereign Neural Constellation"

The blockchain is visualized as a **Star-Field Nebula** where the ₿ symbol is NOT a solid object, but a **constellation of 5,000+ luminous points of light** that transactions spiral into.

### Core Visual Elements

1. **Luminous Sparks** (Transactions)
   - Each transaction = one glowing particle/spark
   - Sparks spawn at screen edges and spiral inward
   - Color based on fee rate and BTC value
   - Size based on transaction value (logarithmic scale)
   - Long motion-blur trails as they travel

2. **The ₿ Constellation** (Target Formation)
   - 5,000+ destination points forming a giant ₿ symbol
   - Points are initially dim/ghosted
   - As sparks arrive and "lock in", points become bright
   - Creates progressive "building" visual as transactions fill the shape

3. **Spiral Vortex Pathing**
   - Sparks DON'T travel in straight lines
   - They spiral toward center while being pulled to their target point
   - Accelerating rotation as they approach
   - Creates mesmerizing, addictive vortex effect

4. **Hyperspace Ascension** (Block Mined Event)
   - When a new block is mined, the entire ₿ constellation WARPS UPWARD
   - All particles turn pure white
   - Extreme upward velocity with light streaks
   - Vertical beam of white light through screen center
   - Constellation clears and rebuilds with next block's transactions

---

## DATA SOURCE: Mempool.space WebSocket API

### Connection
```
WebSocket URL: wss://mempool.space/api/v1/ws
```

### Subscription Message (send on connect)
```json
{
  "action": "want",
  "data": ["blocks", "mempool-blocks", "live-2h-chart", "stats"]
}
```

### Incoming Data Formats

#### New Transaction
```json
{
  "tx": {
    "txid": "abc123def456...",      // 64-char hex string
    "value": 50000000,               // Satoshis (divide by 100000000 for BTC)
    "fee": 5000,                     // Satoshis
    "feeRate": 25.5,                 // sat/vB
    "vsize": 200                     // Virtual bytes
  }
}
```

#### New Block Mined
```json
{
  "block": {
    "height": 880123,
    "tx_count": 3500,
    "size": 1500000,
    "timestamp": 1706425600
  }
}
```

#### Mempool Info
```json
{
  "mempoolInfo": {
    "size": 150000,                  // Transaction count
    "vsize": 200000000               // Virtual size in vBytes
  }
}
```

#### Mempool Blocks (pending blocks)
```json
{
  "mempool-blocks": [
    {
      "blockSize": 1500000,
      "blockVSize": 1000000,
      "nTx": 3000,
      "feeRange": [5, 10, 25, 50, 100, 200]
    }
  ]
}
```

---

## PARTICLE SYSTEM SPECIFICATIONS

### Spark Properties
```cpp
struct TransactionSpark {
    string txid;                     // Transaction ID for mempool.space link
    
    // Position & Motion
    Vector3 position;                // Current world position
    Vector3 velocity;                // Current velocity
    float spiralAngle;               // Current angle in spiral (radians)
    float spiralRadius;              // Distance from center
    float spiralSpeed;               // Angular velocity (rad/frame)
    float approachSpeed;             // Radius decay multiplier (0.992-0.997)
    
    // Target
    Vector3 targetPosition;          // Final constellation position
    bool isLocked;                   // Has reached destination
    float lockFlash;                 // Flash intensity on arrival (0-1)
    
    // Visual
    Color color;                     // Based on fee rate
    float size;                      // Based on BTC value
    float opacity;                   // 1.0 normally
    Trail trail;                     // Motion blur trail
    
    // Data
    float btcValue;                  // Transaction value in BTC
    float feeRate;                   // Fee rate in sat/vB
    int64 timestamp;                 // Creation time
};
```

### Spawn Logic
```cpp
// Spawn at random edge of screen
float angle = Random(0, 2 * PI);
float distance = Max(screenWidth, screenHeight) * 0.7;
position.x = center.x + cos(angle) * distance;
position.y = center.y + sin(angle) * distance;
position.z = 0;  // Or random depth for 3D

// Initialize spiral
spiralAngle = atan2(position.y - center.y, position.x - center.x);
spiralRadius = distance;
spiralSpeed = Random(0.02, 0.04);     // Radians per frame
approachSpeed = Random(0.992, 0.997); // Radius decay
```

### Update Physics (per frame)
```cpp
void UpdateSpark(Spark& spark, float deltaTime) {
    // Store trail point
    spark.trail.AddPoint(spark.position);
    
    // Accelerate spiral
    spark.spiralSpeed += 0.0003;
    spark.spiralAngle += spark.spiralSpeed;
    spark.spiralRadius *= spark.approachSpeed;
    
    // Calculate base spiral position
    Vector3 spiralPos;
    spiralPos.x = center.x + cos(spark.spiralAngle) * spark.spiralRadius;
    spiralPos.y = center.y + sin(spark.spiralAngle) * spark.spiralRadius;
    
    // Blend toward target as radius shrinks
    float targetInfluence = Max(0, 1 - spark.spiralRadius / 400);
    spark.position = Lerp(spiralPos, spark.targetPosition, targetInfluence);
    
    // Check arrival
    float distToTarget = Distance(spark.position, spark.targetPosition);
    if (distToTarget < 3 || spark.spiralRadius < 10) {
        spark.position = spark.targetPosition;
        spark.isLocked = true;
        spark.lockFlash = 1.0;  // Triggers flash effect
    }
}
```

### Color Mapping
```cpp
Color GetSparkColor(float feeRate, float btcValue) {
    // Normal Mode
    if (btcValue >= 5.0) return WHITE;          // Whale transaction
    if (feeRate < 10)    return GREEN (#22c55e); // Low fee
    if (feeRate < 50)    return ORANGE (#f7931a); // Medium fee
    return RED (#ef4444);                        // High fee
    
    // Sovereign Mode (Purple Theme)
    if (btcValue >= 5.0) return WHITE;
    if (feeRate < 10)    return PURPLE_LIGHT (#8b5cf6);
    if (feeRate < 50)    return PURPLE (#a855f7);
    return MAGENTA (#c026d3);
}
```

### Size Calculation
```cpp
float GetSparkSize(float btcValue) {
    // Logarithmic scale: small transactions ~1px, whales ~5px
    return 1.0 + log10(Max(btcValue, 0.01) + 1) * 1.5;
}
```

---

## ₿ CONSTELLATION GEOMETRY

### 5000+ Point Generation Algorithm
The constellation is a filled ₿ symbol with strike-through lines. Points are densely packed.

```cpp
vector<Vector2> Generate5000PointBitcoin() {
    vector<Vector2> coords;
    set<string> seen;  // Prevent duplicates
    
    auto addCoord = [&](float x, float y) {
        // Quantize to 0.25 grid
        float rx = round(x * 4) / 4;
        float ry = round(y * 4) / 4;
        string key = to_string(rx) + "," + to_string(ry);
        if (seen.find(key) == seen.end()) {
            seen.insert(key);
            coords.push_back({rx, ry});
        }
    };
    
    // VERTICAL BAR (left spine)
    for (float y = -65; y <= 65; y += 0.25) {
        for (float x = -25; x <= -17; x += 0.25) {
            addCoord(x, y);
        }
    }
    
    // TOP HORIZONTAL BAR
    for (float x = -16; x <= 15; x += 0.25) {
        for (float y = 58; y <= 65; y += 0.25) {
            addCoord(x, y);
        }
    }
    
    // UPPER CURVE (top bump)
    // Ellipse: center (15, 36), radii (22, 22)
    for (float angle = -PI/2; angle <= PI/2; angle += 0.01) {
        float rx = 22, ry = 22;
        float cx = 15, cy = 36;
        for (float r = 0; r <= 8; r += 0.25) {
            float x = cx + cos(angle) * (rx - r);
            float y = cy + sin(angle) * (ry - r);
            if (x >= -16) addCoord(x, y);
        }
    }
    
    // FILL UPPER SECTION
    for (float x = -16; x <= 15; x += 0.25) {
        for (float y = 15; y <= 57; y += 0.25) {
            float dist = sqrt(pow(x - 15, 2) + pow(y - 36, 2));
            if (dist <= 21) addCoord(x, y);
        }
    }
    
    // MIDDLE BAR
    for (float x = -16; x <= 20; x += 0.25) {
        for (float y = -8; y <= 8; y += 0.25) {
            addCoord(x, y);
        }
    }
    
    // LOWER CURVE (bottom bump - larger)
    // Ellipse: center (20, -32), radii (28, 28)
    for (float angle = -PI/2; angle <= PI/2; angle += 0.008) {
        float rx = 28, ry = 28;
        float cx = 20, cy = -32;
        for (float r = 0; r <= 10; r += 0.25) {
            float x = cx + cos(angle) * (rx - r);
            float y = cy + sin(angle) * (ry - r);
            if (x >= -16) addCoord(x, y);
        }
    }
    
    // FILL LOWER SECTION
    for (float x = -16; x <= 20; x += 0.25) {
        for (float y = -57; y <= -9; y += 0.25) {
            float dist = sqrt(pow(x - 20, 2) + pow(y - (-32), 2));
            if (dist <= 27) addCoord(x, y);
        }
    }
    
    // BOTTOM HORIZONTAL BAR
    for (float x = -16; x <= 22; x += 0.25) {
        for (float y = -65; y <= -58; y += 0.25) {
            addCoord(x, y);
        }
    }
    
    // TOP STRIKE-THROUGH LINES
    for (float x = -23; x <= -14; x += 0.25) {
        for (float y = 66; y <= 80; y += 0.25) addCoord(x, y);
    }
    for (float x = -5; x <= 4; x += 0.25) {
        for (float y = 66; y <= 80; y += 0.25) addCoord(x, y);
    }
    
    // BOTTOM STRIKE-THROUGH LINES
    for (float x = -23; x <= -14; x += 0.25) {
        for (float y = -80; y <= -66; y += 0.25) addCoord(x, y);
    }
    for (float x = -5; x <= 4; x += 0.25) {
        for (float y = -80; y <= -66; y += 0.25) addCoord(x, y);
    }
    
    return coords;  // ~5000+ points
}
```

### Scaling to Screen
```cpp
float scale = Min(screenWidth, screenHeight) / 1000;
float pointSize = 2.5 * scale;

for (auto& coord : bitcoinCoords) {
    Vector3 worldPos;
    worldPos.x = screenCenter.x + coord.x * pointSize;
    worldPos.y = screenCenter.y + coord.y * pointSize;
    worldPos.z = 0;
    constellationPoints.push_back(worldPos);
}
```

---

## HYPERSPACE ASCENSION EFFECT

Triggered when `block` message received from WebSocket.

### Phase 1: Flash (0-100ms)
- All constellation particles turn pure WHITE
- Screen flash/bloom effect

### Phase 2: Warp (100ms-2s)
- All particles accelerate UPWARD at extreme velocity
- Particles stretch into light streaks (motion blur)
- Slight horizontal spread based on distance from center
- Particles fade out as they exit top of screen

### Phase 3: Beam (0-2.5s)
- Vertical beam of white light from bottom to top of screen
- Beam width: 80-120px at center
- Gradient fade to transparent at edges
- Intensity fades over 2.5 seconds

### Implementation
```cpp
struct AscensionBeam {
    float intensity;           // 1.0 -> 0.0 over 2.5s
    float width;              // 80-120 pixels
    vector<AscendingSpark> sparks;
};

struct AscendingSpark {
    Vector3 position;
    float vy;                 // -20 to -60 (upward velocity)
    float vx;                 // Slight horizontal spread
    float size;
    float opacity;            // Fades out
};

void TriggerAscension() {
    ascensionBeam.intensity = 1.0;
    ascensionBeam.width = 80;
    
    // Convert constellation sparks to ascending sparks
    for (auto& spark : constellationSparks) {
        AscendingSpark asc;
        asc.position = spark.position;
        asc.vy = -20 - Random(0, 40);  // Upward
        asc.vx = (spark.position.x - center.x) * 0.02;  // Spread
        asc.size = spark.size;
        asc.opacity = 1.0;
        ascensionBeam.sparks.push_back(asc);
    }
    
    // Clear constellation
    constellationSparks.clear();
    for (auto& point : constellationPoints) {
        point.filled = false;
    }
}

void UpdateAscension(float deltaTime) {
    ascensionBeam.intensity *= 0.98;  // Fade
    
    for (auto& spark : ascensionBeam.sparks) {
        spark.vy -= 2;            // Accelerate upward
        spark.position.y += spark.vy;
        spark.position.x += spark.vx;
        spark.opacity -= 0.015;
    }
    
    // Remove faded sparks
    ascensionBeam.sparks.erase(
        remove_if(sparks.begin(), sparks.end(),
            [](const auto& s) { return s.opacity <= 0; }),
        sparks.end()
    );
}
```

---

## VISUAL EFFECTS CHECKLIST

### Required Shader Features
- [x] Additive blending (overlapping particles = brighter)
- [x] Radial glow/bloom on particles
- [x] Motion blur trails
- [x] HDR bloom for "burning white core" effect
- [x] Screen-space light streaks for ascension

### Particle Rendering
- Each spark should have:
  - Outer glow (colored, 4x size)
  - Core (solid color, 1x size)
  - Hot center (white, 0.3x size)

### Background
- Deep space black (#020204)
- 300+ static twinkling stars
- Optional: subtle nebula clouds

### UI Elements (Optional)
- Block height counter
- Transaction count
- Mempool size
- Fee rate histogram

---

## COLOR PALETTES

### Normal Mode (Bitcoin Orange)
```
Background:     #020204 (near black)
Primary:        #f7931a (Bitcoin orange)
Glow:           #ff9500
Core:           #ffffff
Spark Low:      #22c55e (green)
Spark Medium:   #f7931a (orange)
Spark High:     #ef4444 (red)
Spark Whale:    #ffffff (white)
```

### Sovereign Mode (Purple Theme)
```
Background:     #030206 (purple-black)
Primary:        #a855f7 (purple)
Glow:           #c084fc
Core:           #ffffff
Spark Low:      #8b5cf6 (purple)
Spark Medium:   #a855f7 (purple)
Spark High:     #c026d3 (magenta)
Spark Whale:    #ffffff (white)
```

---

## INTERACTIVITY

### Hover
- Show transaction details on hover:
  - TXID (truncated: first 8 chars...last 8 chars)
  - BTC value
  - Fee rate (sat/vB)

### Click
- Open mempool.space in new tab:
  - URL: `https://mempool.space/tx/{txid}`

---

## COMPLETE JAVASCRIPT SOURCE

The full working JavaScript implementation is in: `static/js/visualizer.js`

This file contains:
- WebSocket connection to mempool.space
- All particle physics
- Spiral vortex motion
- Constellation point generation
- Ascension effect
- Trail rendering
- Color/size calculations

---

## RECOMMENDED GAME ENGINE APPROACH

### Unreal Engine (UE5)
1. Use **Niagara** for particle system
2. GPU particle rendering for 5000+ particles
3. Custom material with additive blending
4. WebSocket plugin for live data

### Unity
1. Use **VFX Graph** for GPU particles
2. Custom shader with HDR bloom
3. WebSocket Sharp for live data

### Godot
1. Use **GPUParticles3D** 
2. Custom shader material
3. WebSocketClient for live data

---

## CREDITS

- Data source: mempool.space (open source Bitcoin explorer)
- Concept: Protocol Pulse "Sovereign Neural Constellation V8"
- Original implementation: JavaScript/Canvas 2D (not suitable for production quality)

---

**Export Date:** January 28, 2026
**Version:** V8 Final
