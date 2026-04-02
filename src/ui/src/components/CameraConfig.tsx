import { useState, useEffect } from "react";

type CameraConfigData =
  | { source_type: "local"; device_index: number }
  | { source_type: "rtsp"; rtsp_url: string };

interface CameraConfigProps {
  camera: CameraConfigData | null;
  onUpdate: (camera: CameraConfigData) => Promise<void>;
}

export default function CameraConfig({ camera, onUpdate }: CameraConfigProps) {
  const [selectedType, setSelectedType] = useState<"local" | "rtsp">(
    camera?.source_type ?? "local",
  );
  const [deviceIndex, setDeviceIndex] = useState(
    camera?.source_type === "local" ? String(camera.device_index) : "",
  );
  const [rtspUrl, setRtspUrl] = useState(
    camera?.source_type === "rtsp" ? camera.rtsp_url : "",
  );
  const [updating, setUpdating] = useState(false);

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
      return (
        (selectedType === "local" && deviceIndex !== "") ||
        (selectedType === "rtsp" && rtspUrl !== "")
      );
    }
    if (selectedType !== camera.source_type) return true;
    if (selectedType === "local" && camera.source_type === "local") {
      const parsed = parseInt(deviceIndex, 10);
      return isNaN(parsed) ? deviceIndex !== "" : parsed !== camera.device_index;
    }
    if (selectedType === "rtsp" && camera.source_type === "rtsp") {
      return rtspUrl !== camera.rtsp_url;
    }
    return false;
  }

  function handleTypeChange(value: string) {
    const newType = value as "local" | "rtsp";
    setSelectedType(newType);
    if (newType === "local") {
      setRtspUrl("");
      setDeviceIndex("");
    } else {
      setDeviceIndex("");
      setRtspUrl("");
    }
  }

  async function handleSubmit() {
    setUpdating(true);
    try {
      if (selectedType === "local") {
        await onUpdate({
          source_type: "local",
          device_index: parseInt(deviceIndex, 10),
        });
      } else {
        await onUpdate({ source_type: "rtsp", rtsp_url: rtspUrl });
      }
    } catch {
      // Error handled by parent via alert
    } finally {
      setUpdating(false);
    }
  }

  const dirty = isDirty();

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
        onChange={(e) => handleTypeChange(e.target.value)}
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
          value={deviceIndex}
          onChange={(e) => setDeviceIndex(e.target.value)}
          min={0}
          style={{
            padding: "8px 12px",
            border: "1px solid #D4DAE0",
            borderRadius: "4px",
            color: "#2C3E50",
            width: "120px",
          }}
        />
      ) : (
        <input
          type="text"
          value={rtspUrl}
          onChange={(e) => setRtspUrl(e.target.value)}
          placeholder="rtsp://..."
          style={{
            padding: "8px 12px",
            border: "1px solid #D4DAE0",
            borderRadius: "4px",
            color: "#2C3E50",
            flex: 1,
          }}
        />
      )}

      <button
        disabled={!dirty || updating}
        onClick={handleSubmit}
        style={{
          padding: "8px 16px",
          backgroundColor: dirty && !updating ? "#5B8CB8" : "#A8C4DC",
          color: "#FFFFFF",
          border: "none",
          borderRadius: "4px",
          cursor: dirty && !updating ? "pointer" : "default",
        }}
      >
        {updating ? "Updating..." : "Update Camera"}
      </button>
    </div>
  );
}
