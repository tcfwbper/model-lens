/**
 * Multi-select dropdown component for choosing which detection labels to monitor.
 * Provides search filtering, bulk select/clear actions, and an explicit update button.
 */
import { useState, useEffect, useRef } from "react";

export interface TargetLabelsProps {
  validLabels: string[];
  activeLabels: string[];
  onUpdate: (labels: string[]) => Promise<void>;
}

export function TargetLabels({ validLabels, activeLabels, onUpdate }: TargetLabelsProps): JSX.Element {
  const [selected, setSelected] = useState<Set<string>>(new Set(activeLabels));
  const [searchTerm, setSearchTerm] = useState("");
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [updating, setUpdating] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Sync from props
  useEffect(() => {
    setSelected(new Set(activeLabels));
  }, [activeLabels]);

  // Click-outside detection
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, []);

  function isDirty(): boolean {
    if (selected.size !== activeLabels.length) return true;
    const sortedSelected = Array.from(selected).sort();
    const sortedActive = [...activeLabels].sort();
    for (let i = 0; i < sortedSelected.length; i++) {
      if (sortedSelected[i] !== sortedActive[i]) return true;
    }
    return false;
  }

  function getTriggerText(): string {
    if (selected.size === 0) return "No labels selected";
    if (selected.size === validLabels.length && validLabels.length > 0) return "All labels selected";
    return `${selected.size} labels selected`;
  }

  function toggleLabel(label: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  }

  function selectAll() {
    setSelected(new Set(validLabels));
  }

  function clearAll() {
    setSelected(new Set());
  }

  async function handleUpdate() {
    setUpdating(true);
    setDropdownOpen(false);
    try {
      await onUpdate(Array.from(selected));
    } catch {
      // Error handled by parent via alert
    } finally {
      setUpdating(false);
    }
  }

  const filteredLabels = validLabels.filter((label) =>
    label.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const buttonEnabled = isDirty() && !updating;

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        aria-label={getTriggerText()}
        style={{
          width: "100%",
          padding: "8px 12px",
          backgroundColor: "#FFFFFF",
          border: "1px solid #D4DAE0",
          borderRadius: "4px",
          textAlign: "left",
          cursor: "pointer",
          color: "#2C3E50",
        }}
      >
        {getTriggerText()}
      </button>
      {dropdownOpen && (
        <div
          style={{
            position: "absolute",
            top: "100%",
            left: "0",
            right: "0",
            backgroundColor: "#FFFFFF",
            border: "1px solid #D4DAE0",
            borderRadius: "4px",
            marginTop: "4px",
            zIndex: 10,
            maxHeight: "300px",
            display: "flex",
            flexDirection: "column",
          }}
        >
          <input
            type="text"
            placeholder="Search labels..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={{
              padding: "8px 12px",
              border: "none",
              borderBottom: "1px solid #D4DAE0",
              outline: "none",
              color: "#2C3E50",
            }}
          />
          <div
            style={{
              display: "flex",
              gap: "8px",
              padding: "4px 12px",
              borderBottom: "1px solid #D4DAE0",
            }}
          >
            <button
              onClick={selectAll}
              style={{
                background: "none",
                border: "none",
                color: "#5B8CB8",
                cursor: "pointer",
                padding: "4px",
                fontSize: "0.85rem",
              }}
            >
              Select All
            </button>
            <button
              onClick={clearAll}
              style={{
                background: "none",
                border: "none",
                color: "#5B8CB8",
                cursor: "pointer",
                padding: "4px",
                fontSize: "0.85rem",
              }}
            >
              Clear All
            </button>
          </div>
          <div style={{ maxHeight: "220px", overflow: "auto" }}>
            {filteredLabels.map((label) => (
              <label
                key={label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "6px 12px",
                  cursor: "pointer",
                  color: "#2C3E50",
                }}
              >
                <input
                  type="checkbox"
                  checked={selected.has(label)}
                  onChange={() => toggleLabel(label)}
                />
                {label}
              </label>
            ))}
          </div>
        </div>
      )}
      <button
        disabled={!buttonEnabled}
        onClick={handleUpdate}
        style={{
          marginTop: "8px",
          padding: "8px 16px",
          backgroundColor: buttonEnabled ? "#5B8CB8" : "#A8C4DC",
          color: "#FFFFFF",
          border: "none",
          borderRadius: "4px",
          cursor: buttonEnabled ? "pointer" : "default",
          width: "100%",
        }}
      >
        {updating ? "Updating..." : "Update Labels"}
      </button>
    </div>
  );
}
