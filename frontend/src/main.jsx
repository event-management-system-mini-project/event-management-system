import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

function App() {
  const [state, setState] = useState("Checking connection...");
  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/health", { signal: controller.signal })
      .then(async (response) => {
        const data = await response.json();
        if (!response.ok || data.status !== "ok" || data.database !== "ok") {
          throw new Error("Unavailable");
        }
        setState("Connected");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setState("Connection unavailable");
      });
    return () => controller.abort();
  }, []);
  return (
    <main>
      <p className="eyebrow">Event Management System</p>
      <h1>A foundation for better events.</h1>
      <p>The local platform is ready for event management and registration modules.</p>
      <section aria-labelledby="connection-heading">
        <h2 id="connection-heading">Service connection</h2>
        <p role="status">{state}</p>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(<App />);
