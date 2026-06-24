/**
 * Camera configuration form component.
 * Allows the user to switch between local and RTSP camera sources
 * and submit updates via the onUpdate callback.
 */
import { useState, useEffect } from "react";

export type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

interface CameraConfigProps {
  camera: CameraConfigData | null;
  onUpdate: (camera: CameraConfigData) => Promise<void>;
}

export function CameraConfig({ camera, onUpdate }: CameraConfigProps): JSX.Element {
  const [selectedType, setSelectedType] = useState<"local" | "rtsp">(
    camera?.source_type ?? "local"
  );
  const [deviceIndex, setDeviceIndex] = useState<string>(
    camera?.source_type === "local" ? String(camera.device_index) : ""
  );
  const [rtspUrl, setRtspUrl] = useState<string>(
    camera?.source_type === "rtsp" ? camera.rtsp_url : ""
  );
  const [updating, setUpdating] = useState(false);

  // Sync from props
  useEffect(() => {
    if (camera) {
      setSelectedType(camera.source_type);
      if (camera.source_type === "local") {
        setDeviceIndex(String(camera.device_index));
        setRtspUrl("");
      } else {
        setRtspUrl(camera.rtsp_url);
        setDeviceIndex("");
      }
    }
  }, [camera]);

  function isDirty(): boolean {
    if (camera === null) {
      if (selectedType === "local" && deviceIndex !== "") return true;
      if (selectedType === "rtsp" && rtspUrl !== "") return true;
      return false;
    }
    if (selectedType !== camera.source_type) return true;
    if (selectedType === "local" && camera.source_type === "local") {
      return parseInt(deviceIndex, 10) !== camera.device_index || (deviceIndex !== "" && isNaN(parseInt(deviceIndex, 10)));
    }
    if (selectedType === "rtsp" && camera.source_type === "rtsp") {
      return rtspUrl !== camera.rtsp_url;
    }
    return false;
  }

  function handleTypeChange(e: React.ChangeEvent<HTMLSelectElement>) {
    setSelectedType(e.target.value as "local" | "rtsp");
    setDeviceIndex("");
    setRtspUrl("");
  }

  async function handleSubmit() {
    setUpdating(true);
    try {
      if (selectedType === "local") {
        await onUpdate({ source_type: "local", device_index: parseInt(deviceIndex, 10) });
      } else {
        await onUpdate({ source_type: "rtsp", rtsp_url: rtspUrl });
      }
    } catch {
      // Error handled by parent via alert
    } finally {
      setUpdating(false);
    }
  }

  const buttonEnabled = isDirty() && !updating;

  return (
    <div
      style={{
        backgroundColor: "#FFFFFF",
        border: "1px solid #D4DAE0",
        borderRadius: "8px",
        padding: "16px",
        display: "flex",
        alignItems: "center",
        gap: "12px",
      }}
    >
      <select
        value={selectedType}
        onChange={handleTypeChange}
        style={{
          padding: "8px 12px",
          border: "1px solid #D4DAE0",
          borderRadius: "4px",
          color: "#2C3E50",
        }}
      >
        <option value="local">Local Camera</option>
        <option value="rtsp">RTSP</option>
      </select>
      {selectedType === "local" ? (
        <input
          type="number"
          min={0}
          value={deviceIndex}
          onChange={(e) => setDeviceIndex(e.target.value)}
          style={{
            width: "120px",
            padding: "8px 12px",
            border: "1px solid #D4DAE0",
            borderRadius: "4px",
            color: "#2C3E50",
          }}
        />
      ) : (
        <input
          type="text"
          placeholder="rtsp://..."
          value={rtspUrl}
          onChange={(e) => setRtspUrl(e.target.value)}
          style={{
            flex: 1,
            padding: "8px 12px",
            border: "1px solid #D4DAE0",
            borderRadius: "4px",
            color: "#2C3E50",
          }}
        />
      )}
      <button
        disabled={!buttonEnabled}
        onClick={handleSubmit}
        style={{
          padding: "8px 16px",
          backgroundColor: buttonEnabled ? "#5B8CB8" : "#A8C4DC",
          color: "#FFFFFF",
          borderStyle: "none",
          borderRadius: "4px",
          cursor: buttonEnabled ? "pointer" : "default",
        }}
      >
        {updating ? "Updating..." : "Update Camera"}
      </button>
    </div>
  );
}
