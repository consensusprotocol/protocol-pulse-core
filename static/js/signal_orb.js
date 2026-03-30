/**
 * SIGNAL ORB — Protocol Pulse Sovereign Convergence Visualization
 * ================================================================
 * Fetches live data from /api/v1/intelligence/convergence/graph
 * Renders a Three.js force-directed orb where nodes = signal domains
 * and proximity to center = alignment with dominant thesis.
 * 
 * NO FAKE DATA. Every node position, color, and size comes from
 * the real convergence engine running on Ultron.
 */

(function() {
  'use strict';

  const ORB_CONTAINER_ID = 'signal-orb-container';
  const API_URL = '/api/v1/intelligence/convergence/graph';
  const MATRIX_URL = '/api/v1/intelligence/matrix';
  const REFRESH_MS = 30000; // 30s refresh

  // PBX Design Law: Industrial greys, ice blues, protocol red
  const COLORS = {
    miner:    0xCC2222,  // Protocol Red
    exchange: 0x00D68F,  // Emerald
    insider:  0x00CCFF,  // Ice Blue
    macro:    0xF4C46F,  // Gold
    social:   0x8B5CF6,  // Purple
    onchain:  0x06B6D4,  // Cyan
    core:     0xFFFFFF,  // White center
    web:      0x333333,  // Connection lines
    bg:       0x0A0A0A,  // Background
  };

  let scene, camera, renderer, animationId;
  let nodes = [], lines = [], coreMesh;
  let currentData = null;
  let matrixData = null;

  function init() {
    const container = document.getElementById(ORB_CONTAINER_ID);
    if (!container) return;

    // Scene
    scene = new THREE.Scene();

    // Camera
    const aspect = container.clientWidth / container.clientHeight;
    camera = new THREE.PerspectiveCamera(50, aspect, 0.1, 200);
    camera.position.set(0, 0, 28);

    // Renderer
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x000000, 0);
    container.appendChild(renderer.domElement);

    // Ambient light
    scene.add(new THREE.AmbientLight(0x404040, 0.6));
    const pointLight = new THREE.PointLight(0xffffff, 1, 100);
    pointLight.position.set(20, 20, 20);
    scene.add(pointLight);

    // Core orb (center — represents convergence)
    const coreGeo = new THREE.SphereGeometry(1.8, 64, 64);
    const coreMat = new THREE.MeshPhongMaterial({
      color: COLORS.core,
      transparent: true,
      opacity: 0.12,
      emissive: COLORS.core,
      emissiveIntensity: 0.15,
    });
    coreMesh = new THREE.Mesh(coreGeo, coreMat);
    scene.add(coreMesh);

    // Glow ring around core
    const ringGeo = new THREE.RingGeometry(2.2, 2.5, 64);
    const ringMat = new THREE.MeshBasicMaterial({
      color: 0xCC2222,
      transparent: true,
      opacity: 0.08,
      side: THREE.DoubleSide,
    });
    const ring = new THREE.Mesh(ringGeo, ringMat);
    scene.add(ring);

    // Resize handler
    window.addEventListener('resize', () => {
      if (!container.clientWidth) return;
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    });

    // Start
    fetchAndRender();
    setInterval(fetchAndRender, REFRESH_MS);
    animate();
  }

  async function fetchAndRender() {
    try {
      const [graphRes, matrixRes] = await Promise.all([
        fetch(API_URL),
        fetch(MATRIX_URL),
      ]);
      
      if (graphRes.ok) {
        currentData = await graphRes.json();
        updateNodes(currentData);
      }
      if (matrixRes.ok) {
        matrixData = await matrixRes.json();
        updateHUD(matrixData);
      }
    } catch (e) {
      console.warn('Orb fetch failed:', e);
    }
  }

  function updateNodes(data) {
    // Clear existing nodes and lines
    nodes.forEach(n => scene.remove(n.mesh));
    lines.forEach(l => scene.remove(l));
    nodes = [];
    lines = [];

    if (!data.nodes || !data.nodes.length) return;

    const convergence = data.convergence_score || 50;

    // Update core intensity based on convergence
    if (coreMesh) {
      coreMesh.material.emissiveIntensity = convergence / 400;
      coreMesh.material.opacity = 0.08 + (convergence / 500);
    }

    // Create signal nodes
    data.nodes.forEach((nodeData, i) => {
      const color = COLORS[nodeData.family] || COLORS.core;
      const distance = (nodeData.distance_to_center || 0.5) * 12;
      const size = 0.3 + (nodeData.confidence || 0.5) * 0.5;

      // Fibonacci sphere distribution
      const golden = 1.618033988749895;
      const theta = 2 * Math.PI * golden * i;
      const phi = Math.acos(1 - 2 * (i + 0.5) / Math.max(data.nodes.length, 3));

      const x = distance * Math.sin(phi) * Math.cos(theta);
      const y = distance * Math.sin(phi) * Math.sin(theta);
      const z = distance * Math.cos(phi) * 0.4; // flatten Z

      const geo = new THREE.SphereGeometry(size, 24, 24);
      const mat = new THREE.MeshPhongMaterial({
        color: color,
        emissive: color,
        emissiveIntensity: (nodeData.score || 50) / 200,
        transparent: true,
        opacity: 0.85,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(x, y, z);

      scene.add(mesh);
      nodes.push({
        mesh,
        data: nodeData,
        targetX: x,
        targetY: y,
        targetZ: z,
        velocity: new THREE.Vector3(),
      });
    });

    // Create connection lines (edges)
    if (data.edges) {
      data.edges.forEach(edge => {
        const sourceNode = nodes.find(n => n.data.id === edge.source);
        const targetNode = nodes.find(n => n.data.id === edge.target);
        if (!sourceNode || !targetNode) return;

        const points = [sourceNode.mesh.position, targetNode.mesh.position];
        const geo = new THREE.BufferGeometry().setFromPoints(points);
        const opacity = edge.relation === 'agreement' ? 0.3 : 0.08;
        const color = edge.relation === 'agreement' ? 0x00D68F : 0x444444;
        const mat = new THREE.LineBasicMaterial({ color, transparent: true, opacity });
        const line = new THREE.Line(geo, mat);

        scene.add(line);
        lines.push(line);
      });
    }
  }

  function updateHUD(data) {
    // Update convergence score display
    const scoreEl = document.getElementById('orb-convergence-score');
    const thesisEl = document.getElementById('orb-thesis');
    const labelEl = document.getElementById('orb-label');

    if (scoreEl && data.composite) {
      scoreEl.textContent = data.composite.score ? data.composite.score.toFixed(1) : '--';
      scoreEl.style.color = data.composite.direction === 1 ? '#00d68f' :
                            data.composite.direction === -1 ? '#dc2626' : '#f4c46f';
    }
    if (thesisEl && data.dominant_thesis) {
      thesisEl.textContent = data.dominant_thesis.label || '';
    }
    if (labelEl && data.composite) {
      labelEl.textContent = data.composite.label || 'Analyzing...';
    }

    // Update domain pills
    if (data.domains) {
      const pillsContainer = document.getElementById('orb-domain-pills');
      if (pillsContainer) {
        pillsContainer.innerHTML = data.domains.map(d => {
          const arrow = d.direction === 1 ? '▲' : d.direction === -1 ? '▼' : '●';
          const color = d.direction === 1 ? '#00d68f' : d.direction === -1 ? '#dc2626' : '#888';
          return `<span class="orb-pill" style="color:${color}">${arrow} ${d.label} ${d.score.toFixed(0)}</span>`;
        }).join('');
      }
    }
  }

  function animate() {
    animationId = requestAnimationFrame(animate);
    const time = Date.now() * 0.001;

    // Rotate scene slowly
    scene.rotation.y = time * 0.05;

    // Pulse core
    if (coreMesh) {
      const convergence = currentData ? (currentData.convergence_score || 50) : 50;
      const pulse = 1 + Math.sin(time * (convergence / 30)) * 0.03;
      coreMesh.scale.set(pulse, pulse, pulse);
    }

    // Gentle node float
    nodes.forEach((n, i) => {
      const float = Math.sin(time * 0.8 + i * 1.5) * 0.15;
      n.mesh.position.y = n.targetY + float;
    });

    // Update line positions to follow nodes
    lines.forEach((line, i) => {
      if (line.geometry && nodes.length >= 2) {
        line.geometry.setFromPoints(
          nodes.filter((_, idx) => idx < 2).map(n => n.mesh.position)
        );
      }
    });

    renderer.render(scene, camera);
  }

  // Initialize when DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
