/**
 * Caption Editor React Components - Reference Implementation
 * 
 * ⚠️  IMPORTANT: This file is REFERENCE CODE for a separate React project
 * 
 * This should NOT be in the Python project directory.
 * 
 * Create a separate React app:
 *   cd c:\dev\
 *   npx create-react-app caption-editor
 *   cd caption-editor
 * 
 * Then copy these component code into:
 *   src/components/VideoPlayer.tsx
 *   src/components/Timeline.tsx
 *   src/components/CaptionEditor.tsx
 *   src/components/StyleControls.tsx
 *   src/components/CaptionEditorApp.tsx
 * 
 * Install dependencies:
 *   npm install axios zustand hls.js @types/hls.js
 * 
 * ============================================================================
 */

// ============================================================================
// 1. VIDEO PLAYER COMPONENT - Display video with caption overlay
// ============================================================================

import React, { useRef, useEffect, useState } from 'react';
import HLS from 'hls.js';

interface Caption {
  id: string;
  text: string;
  start_time: number;
  end_time: number;
}

interface VideoPlayerProps {
  videoUrl: string;
  captions: Caption[];
  currentTime: number;
  onTimeUpdate: (time: number) => void;
}

export const VideoPlayer: React.FC<VideoPlayerProps> = ({
  videoUrl,
  captions,
  currentTime,
  onTimeUpdate,
}) => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [displayedCaption, setDisplayedCaption] = useState<Caption | null>(null);

  useEffect(() => {
    // Find caption that should be displayed at currentTime
    const active = captions.find(
      (cap) => currentTime >= cap.start_time && currentTime < cap.end_time
    );
    setDisplayedCaption(active || null);
  }, [currentTime, captions]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      onTimeUpdate(videoRef.current.currentTime);
    }
  };

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden">
      <video
        ref={videoRef}
        src={videoUrl}
        onTimeUpdate={handleTimeUpdate}
        controls
        className="w-full"
      />

      {/* Caption Overlay */}
      {displayedCaption && (
        <div className="absolute bottom-16 left-0 right-0 flex justify-center pointer-events-none">
          <div className="bg-black bg-opacity-70 px-6 py-3 rounded text-white text-center max-w-2xl">
            <p className="text-xl font-semibold">{displayedCaption.text}</p>
          </div>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// 2. TIMELINE EDITOR - Show captions on a timeline
// ============================================================================

interface TimelineProps {
  captions: Caption[];
  currentTime: number;
  duration: number;
  selectedSegmentId: string | null;
  onSelectSegment: (id: string) => void;
  onSeek: (time: number) => void;
}

export const Timeline: React.FC<TimelineProps> = ({
  captions,
  currentTime,
  duration,
  selectedSegmentId,
  onSelectSegment,
  onSeek,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const pixelsPerSecond = 50; // Zoom level

  return (
    <div
      ref={containerRef}
      className="bg-gray-900 rounded-lg p-4 overflow-x-auto"
    >
      {/* Ruler (time markers) */}
      <div className="flex mb-2 text-xs text-gray-500">
        {Array.from({ length: Math.ceil(duration / 5) }).map((_, i) => (
          <div
            key={i}
            style={{ width: `${5 * pixelsPerSecond}px` }}
            className="text-left"
          >
            {i * 5}s
          </div>
        ))}
      </div>

      {/* Caption blocks */}
      <div className="relative bg-gray-800 rounded h-20" style={{ width: `${duration * pixelsPerSecond}px` }}>
        {/* Playhead indicator */}
        <div
          className="absolute top-0 bottom-0 w-1 bg-red-500 z-10"
          style={{ left: `${currentTime * pixelsPerSecond}px` }}
        />

        {/* Caption segments */}
        {captions.map((caption) => (
          <div
            key={caption.id}
            className={`absolute top-0 bottom-0 flex items-center justify-center text-xs font-semibold cursor-pointer transition ${
              selectedSegmentId === caption.id
                ? 'bg-blue-500 border-2 border-blue-400'
                : 'bg-gray-600 border border-gray-500 hover:bg-gray-500'
            }`}
            style={{
              left: `${caption.start_time * pixelsPerSecond}px`,
              width: `${(caption.end_time - caption.start_time) * pixelsPerSecond}px`,
              minWidth: '30px',
            }}
            onClick={() => onSelectSegment(caption.id)}
          >
            <span className="text-white truncate px-2">{caption.text}</span>
          </div>
        ))}
      </div>

      {/* Playback controls */}
      <div className="mt-2 flex gap-2">
        <button
          onClick={() => onSeek(Math.max(0, currentTime - 1))}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
        >
          -1s
        </button>
        <button
          onClick={() => onSeek(Math.min(duration, currentTime + 1))}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 text-white rounded text-sm"
        >
          +1s
        </button>
      </div>
    </div>
  );
};

// ============================================================================
// 3. CAPTION EDITOR PANEL - Edit text and timing
// ============================================================================

interface CaptionEditorProps {
  segment: Caption | null;
  onUpdate: (updates: Partial<Caption>) => void;
}

export const CaptionEditor: React.FC<CaptionEditorProps> = ({
  segment,
  onUpdate,
}) => {
  const [text, setText] = useState(segment?.text || '');
  const [startTime, setStartTime] = useState(segment?.start_time || 0);
  const [endTime, setEndTime] = useState(segment?.end_time || 5);

  useEffect(() => {
    if (segment) {
      setText(segment.text);
      setStartTime(segment.start_time);
      setEndTime(segment.end_time);
    }
  }, [segment]);

  const handleSave = () => {
    if (segment) {
      onUpdate({
        text,
        start_time: startTime,
        end_time: endTime,
      });
    }
  };

  if (!segment) {
    return (
      <div className="bg-gray-800 p-4 rounded text-gray-400">
        Select a caption segment to edit
      </div>
    );
  }

  return (
    <div className="bg-gray-800 p-4 rounded space-y-4">
      <div>
        <label className="block text-sm font-semibold text-gray-200 mb-2">
          Caption Text
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 outline-none"
          rows={3}
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-2">
            Start Time (s)
          </label>
          <input
            type="number"
            value={startTime}
            onChange={(e) => setStartTime(parseFloat(e.target.value))}
            step={0.1}
            className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 outline-none"
          />
        </div>

        <div>
          <label className="block text-sm font-semibold text-gray-200 mb-2">
            End Time (s)
          </label>
          <input
            type="number"
            value={endTime}
            onChange={(e) => setEndTime(parseFloat(e.target.value))}
            step={0.1}
            className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600 focus:border-blue-500 outline-none"
          />
        </div>
      </div>

      <div>
        <p className="text-sm text-gray-400 mb-2">
          Duration: {(endTime - startTime).toFixed(2)}s
        </p>
      </div>

      <button
        onClick={handleSave}
        className="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded font-semibold"
      >
        Save Changes
      </button>
    </div>
  );
};

// ============================================================================
// 4. STYLE CONTROLS - Global and per-caption styling
// ============================================================================

interface GlobalStyleProps {
  style: {
    font_name: string;
    font_size: number;
    font_color: string;
    position_x: number;
    position_y: number;
  };
  onStyleChange: (key: string, value: any) => void;
  syncMode: boolean;
  onSyncModeChange: (enabled: boolean) => void;
}

export const StyleControls: React.FC<GlobalStyleProps> = ({
  style,
  onStyleChange,
  syncMode,
  onSyncModeChange,
}) => {
  return (
    <div className="bg-gray-800 p-4 rounded space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white">Global Style</h3>
        <label className="flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={syncMode}
            onChange={(e) => onSyncModeChange(e.target.checked)}
            className="w-4 h-4"
          />
          Sync Mode
        </label>
      </div>

      {/* Font Selection */}
      <div>
        <label className="block text-sm font-semibold text-gray-200 mb-2">
          Font Family
        </label>
        <select
          value={style.font_name}
          onChange={(e) => onStyleChange('font_name', e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 text-white rounded border border-gray-600"
        >
          <option>Arial</option>
          <option>Times New Roman</option>
          <option>Courier New</option>
          <option>Verdana</option>
        </select>
      </div>

      {/* Font Size */}
      <div>
        <label className="block text-sm font-semibold text-gray-200 mb-2">
          Font Size: {style.font_size}px
        </label>
        <input
          type="range"
          min={20}
          max={200}
          value={style.font_size}
          onChange={(e) => onStyleChange('font_size', parseInt(e.target.value))}
          className="w-full"
        />
      </div>

      {/* Font Color */}
      <div>
        <label className="block text-sm font-semibold text-gray-200 mb-2">
          Font Color
        </label>
        <input
          type="color"
          value={style.font_color}
          onChange={(e) => onStyleChange('font_color', e.target.value)}
          className="w-full h-10 cursor-pointer"
        />
      </div>

      {/* Position */}
      <div className="space-y-2">
        <label className="block text-sm font-semibold text-gray-200">
          Vertical Position: {Math.round(style.position_y * 100)}%
        </label>
        <input
          type="range"
          min={0}
          max={1}
          step={0.1}
          value={style.position_y}
          onChange={(e) => onStyleChange('position_y', parseFloat(e.target.value))}
          className="w-full"
        />
      </div>
    </div>
  );
};

// ============================================================================
// 5. MAIN EDITOR COMPONENT - Combine all parts
// ============================================================================

interface MainEditorProps {
  projectId: string;
  videoUrl: string;
}

export const CaptionEditorApp: React.FC<MainEditorProps> = ({
  projectId,
  videoUrl,
}) => {
  const [project, setProject] = useState<any>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedSegmentId, setSelectedSegmentId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  // Fetch project data
  useEffect(() => {
    fetch(`/api/projects/${projectId}`)
      .then((res) => res.json())
      .then((data) => {
        setProject(data);
        setLoading(false);
      });
  }, [projectId]);

  // Handle segment update
  const handleSegmentUpdate = (updates: Partial<Caption>) => {
    if (!selectedSegmentId) return;

    fetch(`/api/projects/${projectId}/segments/${selectedSegmentId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    })
      .then((res) => res.json())
      .then(() => {
        // Refresh project
        fetch(`/api/projects/${projectId}`)
          .then((res) => res.json())
          .then((data) => setProject(data));
      });
  };

  if (loading) return <div className="text-white">Loading...</div>;

  const selectedSegment = project.segments.find(
    (seg: Caption) => seg.id === selectedSegmentId
  ) || null;

  return (
    <div className="min-h-screen bg-gray-900 text-white p-6">
      <h1 className="text-3xl font-bold mb-6">Caption Editor</h1>

      <div className="grid grid-cols-3 gap-6">
        {/* Left: Video Preview */}
        <div className="col-span-2">
          <VideoPlayer
            videoUrl={videoUrl}
            captions={project.segments}
            currentTime={currentTime}
            onTimeUpdate={setCurrentTime}
          />

          <div className="mt-4">
            <Timeline
              captions={project.segments}
              currentTime={currentTime}
              duration={100} // TODO: Get actual duration
              selectedSegmentId={selectedSegmentId}
              onSelectSegment={setSelectedSegmentId}
              onSeek={setCurrentTime}
            />
          </div>
        </div>

        {/* Right: Controls */}
        <div className="space-y-4">
          <CaptionEditor
            segment={selectedSegment}
            onUpdate={handleSegmentUpdate}
          />

          <StyleControls
            style={project.global_style}
            onStyleChange={(key, value) =>
              fetch(`/api/projects/${projectId}/style`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [key]: value }),
              })
            }
            syncMode={project.sync_mode}
            onSyncModeChange={(enabled) =>
              fetch(`/api/projects/${projectId}/sync-mode`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ sync_mode: enabled }),
              })
            }
          />

          {/* Export Button */}
          <button
            onClick={() => {
              fetch(`/api/projects/${projectId}/export`, {
                method: 'POST',
              })
                .then((res) => res.json())
                .then((data) => {
                  alert('Export complete! ' + data.download_url);
                });
            }}
            className="w-full px-4 py-3 bg-green-600 hover:bg-green-700 text-white rounded font-semibold"
          >
            Export Video
          </button>
        </div>
      </div>
    </div>
  );
};
