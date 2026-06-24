/**
 * Static presentational component that renders the application title bar.
 */
export function Header(): JSX.Element {
  return (
    <header
      style={{
        background: "#FFFFFF",
        borderBottom: "1px solid #D4DAE0",
        padding: "12px 24px",
      }}
    >
      <h1 style={{ fontWeight: "bold", fontSize: "1.5rem", color: "#2C3E50", margin: 0 }}>
        ModelLens
      </h1>
    </header>
  );
}
