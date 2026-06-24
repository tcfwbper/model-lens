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

  return (
    <div ref={containerRef}>
      <button
        onClick={() => setDropdownOpen(!dropdownOpen)}
        aria-label={getTriggerText()}
      >
        {getTriggerText()}
      </button>
      {dropdownOpen && (
        <div>
          <input
            type="text"
            placeholder="Search labels..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <div>
            <button onClick={selectAll}>Select All</button>
            <button onClick={clearAll}>Clear All</button>
          </div>
          <div style={{ maxHeight: "220px", overflow: "auto" }}>
            {filteredLabels.map((label) => (
              <label key={label} style={{ display: "block" }}>
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
        disabled={!isDirty() || updating}
        onClick={handleUpdate}
      >
        {updating ? "Updating..." : "Update Labels"}
      </button>
    </div>
  );
}
