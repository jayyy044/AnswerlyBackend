// // GlassCard.jsx
// import { useState, useEffect, useRef } from 'react';
// import './GlassCard.css';

// const GlassCard = ({ 
//   children, 
//   className = '',
//   showControls: externalShowControls,
//   ...props 
// }) => {
//   const [showControls, setShowControls] = useState(false);
//   const [settings, setSettings] = useState({
//     blurAmount: 5,
//     bgOpacity: 0.55,
//     contentBgOpacity: 0,
//     borderOpacity: 0.025,
//     glowIntensity: 0.0,
//     glowColor: '#783CDC', // Purple
//     noiseOpacity: 0.08,
//     borderRadius: 18
//   });

//   const updateSetting = (key, value) => {
//     setSettings(prev => ({ ...prev, [key]: parseFloat(value) }));
//   };

//   const hexToRgb = (hex) => {
//     const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
//     return result ? {
//       r: parseInt(result[1], 16),
//       g: parseInt(result[2], 16),
//       b: parseInt(result[3], 16)
//     } : { r: 120, g: 60, b: 220 };
//   };

//   const rgb = hexToRgb(settings.glowColor);
//   const glowColorRgba = `rgba(${rgb.r}, ${rgb.g}, ${rgb.b}, ${settings.glowIntensity})`;

//   // Use external control if provided, otherwise use internal state
//   const controlsVisible = externalShowControls !== undefined ? externalShowControls : showControls;

//   return (
//     <>
//       <div
//         className={`glass-card-wrapper ${className}`}
//         style={{ borderRadius: `${settings.borderRadius}px` }}
//         {...props}
//       >
//         {/* Glassmorphic backdrop */}
//         <div 
//           className="glass-card-backdrop"
//           style={{
//             backdropFilter: `blur(${settings.blurAmount}px)`,
//             WebkitBackdropFilter: `blur(${settings.blurAmount}px)`,
//             backgroundColor: `rgba(0, 0, 0, ${settings.bgOpacity})`,
//             borderRadius: `${settings.borderRadius}px`
//           }}
//         ></div>

//         {/* Border glow effect */}
//         <div 
//           className="glass-card-border-glow"
//           style={{
//             borderColor: `rgba(255, 255, 255, ${settings.borderOpacity})`,
//             boxShadow: `0 0 20px ${glowColorRgba}`,
//             borderRadius: `${settings.borderRadius}px`
//           }}
//         ></div>

//         {/* Noise texture overlay */}
//         <div 
//           className="glass-card-noise"
//           style={{ opacity: settings.noiseOpacity }}
//         ></div>

//         {/* Content container */}
//         <div 
//           className="glass-card-content"
//           style={{
//             backgroundColor: `rgba(0, 0, 0, ${settings.contentBgOpacity})`,
//             borderRadius: `${settings.borderRadius}px`
//           }}
//         >
//           {children}
//         </div>
//       </div>

//       {/* Control Panel Toggle Button */}
//       {externalShowControls === undefined && (
//         <button 
//           className="glass-controls-toggle"
//           onClick={() => setShowControls(!showControls)}
//         >
//           {showControls ? '✕' : '🎨'}
//         </button>
//       )}

//       {/* Control Panel */}
//       {controlsVisible && (
//         <div className="glass-controls">
//           <h3>Glass Card Settings</h3>

//           <div className="glass-control-group">
//             <label>
//               Blur Amount: <span className="glass-value">{settings.blurAmount}px</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="100"
//               step="5"
//               value={settings.blurAmount}
//               onChange={(e) => updateSetting('blurAmount', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Background Opacity: <span className="glass-value">{settings.bgOpacity.toFixed(2)}</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="1"
//               step="0.05"
//               value={settings.bgOpacity}
//               onChange={(e) => updateSetting('bgOpacity', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Content Opacity: <span className="glass-value">{settings.contentBgOpacity.toFixed(2)}</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="1"
//               step="0.05"
//               value={settings.contentBgOpacity}
//               onChange={(e) => updateSetting('contentBgOpacity', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Border Opacity: <span className="glass-value">{settings.borderOpacity.toFixed(2)}</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="1"
//               step="0.05"
//               value={settings.borderOpacity}
//               onChange={(e) => updateSetting('borderOpacity', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Glow Intensity: <span className="glass-value">{settings.glowIntensity.toFixed(2)}</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="1"
//               step="0.05"
//               value={settings.glowIntensity}
//               onChange={(e) => updateSetting('glowIntensity', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Glow Color: <span className="glass-value">{settings.glowColor}</span>
//             </label>
//             <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
//               <input
//                 type="color"
//                 value={settings.glowColor}
//                 onChange={(e) => setSettings(prev => ({ ...prev, glowColor: e.target.value }))}
//                 style={{ width: '50px', height: '35px', cursor: 'pointer', border: 'none', borderRadius: '4px' }}
//               />
//               <input
//                 type="text"
//                 value={settings.glowColor}
//                 onChange={(e) => setSettings(prev => ({ ...prev, glowColor: e.target.value }))}
//                 style={{ 
//                   flex: 1, 
//                   padding: '6px 10px', 
//                   background: 'rgba(255,255,255,0.1)', 
//                   border: '1px solid rgba(255,255,255,0.2)',
//                   borderRadius: '4px',
//                   color: 'white',
//                   fontSize: '12px'
//                 }}
//               />
//             </div>
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Noise Opacity: <span className="glass-value">{settings.noiseOpacity.toFixed(2)}</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="0.2"
//               step="0.01"
//               value={settings.noiseOpacity}
//               onChange={(e) => updateSetting('noiseOpacity', e.target.value)}
//             />
//           </div>

//           <div className="glass-control-group">
//             <label>
//               Border Radius: <span className="glass-value">{settings.borderRadius}px</span>
//             </label>
//             <input
//               type="range"
//               min="0"
//               max="50"
//               step="2"
//               value={settings.borderRadius}
//               onChange={(e) => updateSetting('borderRadius', e.target.value)}
//             />
//           </div>
//         </div>
//       )}
//     </>
//   );
// };

// export default GlassCard;


// GlassCard.jsx
import React from 'react';
import './GlassCard.css';

const GlassCard = ({ 
  children, 
  className = '',
  blurAmount = 5,
  bgOpacity = 0.0,
  contentBgOpacity = 0,
  borderOpacity = 0.025,
  noiseOpacity = 0.08,
  borderRadius = 18,
  ...props 
}) => {

  return (
    <div
      className={`glass-card-wrapper ${className}`}
      style={{ borderRadius: `${borderRadius}px` }}
      {...props}
    >
      {/* Glassmorphic backdrop */}
      <div 
        className="glass-card-backdrop"
        style={{
          backdropFilter: `blur(${blurAmount}px)`,
          WebkitBackdropFilter: `blur(${blurAmount}px)`,
          backgroundColor: `rgba(0, 0, 0, ${bgOpacity})`,
          borderRadius: `${borderRadius}px`
        }}
      ></div>

      {/* Border effect */}
      <div 
        className="glass-card-border-glow"
        style={{
          borderColor: `rgba(255, 255, 255, ${borderOpacity})`,
          borderRadius: `${borderRadius}px`
        }}
      ></div>

      {/* Noise texture overlay */}
      <div 
        className="glass-card-noise"
        style={{ opacity: noiseOpacity }}
      ></div>

      {/* Content container */}
      <div 
        className="glass-card-content"
        style={{
          backgroundColor: `rgba(0, 0, 0, ${contentBgOpacity})`,
          borderRadius: `${borderRadius}px`
        }}
      >
        {children}
      </div>
    </div>
  );
};

export default GlassCard;
