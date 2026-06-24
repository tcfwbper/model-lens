/**
 * Fixture builders for UI test suites.
 * Provides factory functions to construct common test data objects
 * without repeating boilerplate across test files.
 */

// --- Types (mirrors production types for test isolation) ---

export interface CameraConfigLocal {
  source_type: "local";
  device_index: number;
}

export interface CameraConfigRtsp {
  source_type: "rtsp";
  rtsp_url: string;
}

export type CameraConfigData = CameraConfigLocal | CameraConfigRtsp;

export interface RuntimeConfig {
  camera: CameraConfigData;
  confidence_threshold: number;
  target_labels: string[];
}

export interface Detection {
  label: string;
  confidence: number;
  bounding_box: [number, number, number, number];
  is_target: boolean;
}

export interface FrameData {
  jpeg_b64: string;
  timestamp: number;
  source: string;
  detections: Detection[];
}

// --- Fixture Builders ---

export function buildLocalCamera(
  overrides: Partial<CameraConfigLocal> = {}
): CameraConfigLocal {
  return {
    source_type: "local",
    device_index: 0,
    ...overrides,
  };
}

export function buildRtspCamera(
  overrides: Partial<CameraConfigRtsp> = {}
): CameraConfigRtsp {
  return {
    source_type: "rtsp",
    rtsp_url: "rtsp://default",
    ...overrides,
  };
}

export function buildRuntimeConfig(
  overrides: Partial<RuntimeConfig> = {}
): RuntimeConfig {
  return {
    camera: buildLocalCamera(),
    confidence_threshold: 0.5,
    target_labels: ["cat"],
    ...overrides,
  };
}

export function buildDetection(
  overrides: Partial<Detection> = {}
): Detection {
  return {
    label: "cat",
    confidence: 0.87,
    bounding_box: [0.1, 0.2, 0.5, 0.6],
    is_target: true,
    ...overrides,
  };
}

export function buildFrameData(
  overrides: Partial<FrameData> = {}
): FrameData {
  return {
    jpeg_b64: "abc",
    timestamp: 1,
    source: "cam",
    detections: [],
    ...overrides,
  };
}
