import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import './ParticleBackground.css';

const ParticleBackground = ({ children }) => {
  const canvasRef = useRef(null);
  const rendererRef = useRef(null);
  const animationIdRef = useRef(null);
  const materialsRef = useRef({});
  const [isLoaded, setIsLoaded] = useState(false);
  const [showControls, setShowControls] = useState(false);
  // const [showChildren, setShowChildren] = useState(false);
  // const delay = isSignupPage ? 10 : 250;

  const [controls, setControls] = useState({
    speed: 0.4,
    noiseScale: 0.6,
    noiseIntensity: 0.52,
    timeScale: 1.0,
    focus: 3.8,
    aperture: 1.79,
    pointSize: 10.0,
    opacity: 0.8,
    planeScale: 10.0,
    vignetteDarkness: 1.5,
    vignetteOffset: 0.4
  });

  const updateControl = (key, value) => {
    setControls(prev => ({ ...prev, [key]: parseFloat(value) }));
  };

  // useEffect(() => {
  //   if (isLoaded) {
  //     // Wait 100-300ms after particles load before showing children
  //     const timer = setTimeout(() => {
  //       setShowChildren(true);
  //     }, delay); // Adjust this delay as needed
      
  //     return () => clearTimeout(timer);
  //   }
  // }, [isLoaded]);

  useEffect(() => {
    if (!canvasRef.current) return;

    // Vertex Shader
    const vertexShader = `
      uniform sampler2D positionsTexture;
      uniform sampler2D initialPositionsTexture;
      uniform float uTime;
      uniform float uFocus;
      uniform float uBlur;
      uniform float uPointSize;
      
      varying float vDistance;
      varying float vPosY;
      varying vec3 vInitialPosition;
      
      void main() {
        vec2 uv = position.xy;
        vec3 pos = texture2D(positionsTexture, uv).xyz;
        vec3 initialPos = texture2D(initialPositionsTexture, uv).xyz;
        
        vec4 mvPosition = modelViewMatrix * vec4(pos, 1.0);
        gl_Position = projectionMatrix * mvPosition;
        
        vDistance = abs(uFocus - (-mvPosition.z));
        vPosY = pos.y;
        vInitialPosition = initialPos;
        
        gl_PointSize = max(vDistance * uBlur * uPointSize, 2.0);
      }
    `;
    
    // Fragment Shader
    const fragmentShader = `
      uniform float uOpacity;
      uniform float uRevealFactor;
      uniform float uTime;
      
      varying float vDistance;
      varying float vPosY;
      varying vec3 vInitialPosition;
      
      float periodicNoise(vec3 p, float time) {
        float noise = 0.0;
        noise += sin(p.x * 2.0 + time) * cos(p.z * 1.5 + time);
        noise += sin(p.x * 3.2 + time * 2.0) * cos(p.z * 2.1 + time) * 0.6;
        noise += sin(p.x * 1.7 + time) * cos(p.z * 2.8 + time * 3.0) * 0.4;
        noise += sin(p.x * p.z * 0.5 + time * 2.0) * 0.3;
        return noise * 0.3;
      }
      
      float sparkleNoise(vec3 seed, float time) {
        float hash = sin(seed.x * 127.1 + seed.y * 311.7 + seed.z * 74.7) * 43758.5453;
        hash = fract(hash);
        
        float sparkle = 0.0;
        sparkle += sin(time + hash * 6.28318) * 0.5;
        sparkle += sin(time * 1.7 + hash * 12.56636) * 0.3;
        
        float normalizedSparkle = (sparkle + 1.0) * 0.5;
        float smoothCurve = pow(normalizedSparkle, 4.0);
        float blendFactor = normalizedSparkle * normalizedSparkle;
        float finalBrightness = mix(normalizedSparkle, smoothCurve, blendFactor);
        
        return 0.7 + finalBrightness * 1.3;
      }
      
      void main() {
        vec2 cxy = 2.0 * gl_PointCoord - 1.0;
        float sdf = length(cxy) - 0.5;
        
        if (sdf > 0.0) discard;
        
        float distanceFromCenter = length(vInitialPosition.xz);
        float noiseValue = periodicNoise(vInitialPosition * 4.0, 0.0);
        float revealThreshold = uRevealFactor + noiseValue * 0.3;
        float revealMask = 1.0 - smoothstep(revealThreshold - 0.2, revealThreshold + 0.1, distanceFromCenter);
        
        float sparkleBrightness = sparkleNoise(vInitialPosition, uTime);
        
        float alpha = (1.04 - clamp(vDistance, 0.0, 1.0)) * 
                     clamp(smoothstep(-0.5, 0.25, vPosY), 0.0, 1.0) * 
                     uOpacity * revealMask * sparkleBrightness;
        
        gl_FragColor = vec4(vec3(1.0), alpha);
      }
    `;
    
    // Simulation shaders
    const simulationVertexShader = `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `;
    
    const simulationFragmentShader = `
      uniform sampler2D positions;
      uniform float uTime;
      uniform float uNoiseScale;
      uniform float uNoiseIntensity;
      uniform float uTimeScale;
      
      varying vec2 vUv;
      
      float periodicNoise(vec3 p, float time) {
        float noise = 0.0;
        noise += sin(p.x * 2.0 + time) * cos(p.z * 1.5 + time);
        noise += sin(p.x * 3.2 + time * 2.0) * cos(p.z * 2.1 + time) * 0.6;
        noise += sin(p.x * 1.7 + time) * cos(p.z * 2.8 + time * 3.0) * 0.4;
        noise += sin(p.x * p.z * 0.5 + time * 2.0) * 0.3;
        return noise * 0.3;
      }
      
      void main() {
        vec3 originalPos = texture2D(positions, vUv).rgb;
        float continuousTime = uTime * uTimeScale;
        
        vec3 noiseInput = originalPos * uNoiseScale;
        
        float displacementX = periodicNoise(noiseInput + vec3(0.0, 0.0, 0.0), continuousTime);
        float displacementY = periodicNoise(noiseInput + vec3(50.0, 0.0, 0.0), continuousTime + 2.094);
        float displacementZ = periodicNoise(noiseInput + vec3(0.0, 50.0, 0.0), continuousTime + 4.188);
        
        vec3 distortion = vec3(displacementX, displacementY, displacementZ) * uNoiseIntensity;
        vec3 finalPos = originalPos + distortion;
        
        gl_FragColor = vec4(finalPos, 1.0);
      }
    `;

    // Scene setup
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(
      50,
      window.innerWidth / window.innerHeight,
      0.01,
      300
    );
    camera.position.set(1.2629783123314589, 2.664606471394044, -1.8178993743288914);
    camera.lookAt(0, 0, 0);

    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: false
    });
    renderer.setClearColor(0x000000, 1);
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    rendererRef.current = renderer;

    // Particle parameters
    const SIZE = 512;
    const PARTICLES = SIZE * SIZE;
    const SCALE = controls.planeScale;

    // Create initial positions texture
    function createPositionsTexture() {
      const data = new Float32Array(PARTICLES * 4);
      for (let i = 0; i < PARTICLES; i++) {
        const i4 = i * 4;
        const x = (i % SIZE) / (SIZE - 1);
        const z = Math.floor(i / SIZE) / (SIZE - 1);
        
        data[i4 + 0] = (x - 0.5) * 2 * SCALE;
        data[i4 + 1] = 0;
        data[i4 + 2] = (z - 0.5) * 2 * SCALE;
        data[i4 + 3] = 1.0;
      }
      
      const texture = new THREE.DataTexture(
        data,
        SIZE,
        SIZE,
        THREE.RGBAFormat,
        THREE.FloatType
      );
      texture.needsUpdate = true;
      return texture;
    }

    const initialPositionsTexture = createPositionsTexture();

    // Create FBO for simulation
    const simulationTarget = new THREE.WebGLRenderTarget(SIZE, SIZE, {
      minFilter: THREE.NearestFilter,
      magFilter: THREE.NearestFilter,
      format: THREE.RGBAFormat,
      type: THREE.FloatType
    });

    // Simulation scene
    const simulationScene = new THREE.Scene();
    const simulationCamera = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);

    const simulationMaterial = new THREE.ShaderMaterial({
      vertexShader: simulationVertexShader,
      fragmentShader: simulationFragmentShader,
      uniforms: {
        positions: { value: initialPositionsTexture },
        uTime: { value: 0 },
        uNoiseScale: { value: controls.noiseScale },
        uNoiseIntensity: { value: controls.noiseIntensity },
        uTimeScale: { value: controls.timeScale }
      }
    });

    const simulationGeometry = new THREE.PlaneGeometry(2, 2);
    const simulationMesh = new THREE.Mesh(simulationGeometry, simulationMaterial);
    simulationScene.add(simulationMesh);

    // Particle positions
    const particlePositions = new Float32Array(PARTICLES * 3);
    for (let i = 0; i < PARTICLES; i++) {
      const i3 = i * 3;
      particlePositions[i3 + 0] = (i % SIZE) / SIZE;
      particlePositions[i3 + 1] = i / SIZE / SIZE;
      particlePositions[i3 + 2] = 0;
    }

    // Particle material
    const particleMaterial = new THREE.ShaderMaterial({
      vertexShader,
      fragmentShader,
      uniforms: {
        positionsTexture: { value: simulationTarget.texture },
        initialPositionsTexture: { value: initialPositionsTexture },
        uTime: { value: 0 },
        uFocus: { value: controls.focus },
        uBlur: { value: controls.aperture },
        uPointSize: { value: controls.pointSize },
        uOpacity: { value: controls.opacity },
        uRevealFactor: { value: 0.0 }
      },
      transparent: true,
      depthWrite: false
    });

    materialsRef.current = { simulationMaterial, particleMaterial };

    const particleGeometry = new THREE.BufferGeometry();
    particleGeometry.setAttribute(
      'position',
      new THREE.BufferAttribute(particlePositions, 3)
    );

    const particles = new THREE.Points(particleGeometry, particleMaterial);
    scene.add(particles);

    // Reveal animation
    let revealStartTime = null;
    const revealDuration = 3.5;
    const clock = new THREE.Clock();

    // Animation loop
    function animate() {
      animationIdRef.current = requestAnimationFrame(animate);

      const elapsedTime = clock.getElapsedTime();

      if (revealStartTime === null) {
        revealStartTime = elapsedTime;
      }

      const revealElapsed = elapsedTime - revealStartTime;
      const revealProgress = Math.min(revealElapsed / revealDuration, 1.0);
      const easedProgress = 1 - Math.pow(1 - revealProgress, 3);
      const revealFactor = easedProgress * 4.0;

      // Update simulation
      simulationMaterial.uniforms.uTime.value = elapsedTime;
      simulationMaterial.uniforms.uTimeScale.value = controls.timeScale * controls.speed;
      renderer.setRenderTarget(simulationTarget);
      renderer.render(simulationScene, simulationCamera);
      renderer.setRenderTarget(null);

      // Update particles
      particleMaterial.uniforms.uTime.value = elapsedTime;
      particleMaterial.uniforms.uRevealFactor.value = revealFactor;

      renderer.render(scene, camera);
      if (!isLoaded) {
        setIsLoaded(true);
      }

    }

    animate();

    // Handle resize
    const handleResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }
      if (rendererRef.current) {
        rendererRef.current.dispose();
      }
      particleGeometry.dispose();
      particleMaterial.dispose();
      simulationGeometry.dispose();
      simulationMaterial.dispose();
      simulationTarget.dispose();
      initialPositionsTexture.dispose();
    };
  }, []);

  // Update uniforms when controls change
  useEffect(() => {
    if (materialsRef.current.simulationMaterial) {
      materialsRef.current.simulationMaterial.uniforms.uNoiseScale.value = controls.noiseScale;
      materialsRef.current.simulationMaterial.uniforms.uNoiseIntensity.value = controls.noiseIntensity;
      materialsRef.current.simulationMaterial.uniforms.uTimeScale.value = controls.timeScale;
    }
    if (materialsRef.current.particleMaterial) {
      materialsRef.current.particleMaterial.uniforms.uFocus.value = controls.focus;
      materialsRef.current.particleMaterial.uniforms.uBlur.value = controls.aperture;
      materialsRef.current.particleMaterial.uniforms.uPointSize.value = controls.pointSize;
      materialsRef.current.particleMaterial.uniforms.uOpacity.value = controls.opacity;
    }
  }, [controls]);

  return (
    <div className="particle-background-container">
      <canvas ref={canvasRef} className="particle-canvas" />
      
      {/* Control Panel */}
      <button 
        className="controls-toggle"
        onClick={() => setShowControls(!showControls)}
      >
        {showControls ? '✕' : '⚙️'}
      </button>
      
      {showControls && (
        <div className="particle-controls">
          <h3>Particle Controls</h3>
          
          <div className="control-group">
            <label>
              Speed: <span className="value">{controls.speed.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={controls.speed}
              onChange={(e) => updateControl('speed', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Noise Scale: <span className="value">{controls.noiseScale.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="5"
              step="0.1"
              value={controls.noiseScale}
              onChange={(e) => updateControl('noiseScale', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Noise Intensity: <span className="value">{controls.noiseIntensity.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={controls.noiseIntensity}
              onChange={(e) => updateControl('noiseIntensity', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Time Scale: <span className="value">{controls.timeScale.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={controls.timeScale}
              onChange={(e) => updateControl('timeScale', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Focus: <span className="value">{controls.focus.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="20"
              step="0.1"
              value={controls.focus}
              onChange={(e) => updateControl('focus', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Aperture (Blur): <span className="value">{controls.aperture.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.01"
              value={controls.aperture}
              onChange={(e) => updateControl('aperture', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Point Size: <span className="value">{controls.pointSize.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="10"
              step="0.1"
              value={controls.pointSize}
              onChange={(e) => updateControl('pointSize', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Opacity: <span className="value">{controls.opacity.toFixed(2)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="1"
              step="0.01"
              value={controls.opacity}
              onChange={(e) => updateControl('opacity', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Plane Scale: <span className="value">{controls.planeScale.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0.1"
              max="20"
              step="0.1"
              value={controls.planeScale}
              onChange={(e) => updateControl('planeScale', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Vignette Darkness: <span className="value">{controls.vignetteDarkness.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={controls.vignetteDarkness}
              onChange={(e) => updateControl('vignetteDarkness', e.target.value)}
            />
          </div>

          <div className="control-group">
            <label>
              Vignette Offset: <span className="value">{controls.vignetteOffset.toFixed(1)}</span>
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={controls.vignetteOffset}
              onChange={(e) => updateControl('vignetteOffset', e.target.value)}
            />
          </div>
        </div>
      )}
      
      {/* Content wrapper - everything passed as children renders on top */}
      <div className={`particle-content ${isLoaded  ? "fade-in" : "hidden"}`}>
        {children}
      </div>
    </div>
  );
};

export default ParticleBackground;