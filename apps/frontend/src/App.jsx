const serviceCards = [
  {
    name: 'Gateway',
    description:
      'Single entry point for the frontend and future external GraphQL clients.',
    path: '/health',
    port: 4000,
  },
  {
    name: 'Identity/Access Service',
    description:
      'Standard Django service placeholder for identity and authorization concerns.',
    path: '/health/',
    port: 8001,
  },
  {
    name: 'CRM Relationships Service',
    description:
      'Standard Django service placeholder for companies, contacts, activities, and tasks.',
    path: '/health/',
    port: 8002,
  },
  {
    name: 'Deals Service',
    description:
      'Standard Django service placeholder for deal ownership and lifecycle behavior.',
    path: '/health/',
    port: 8003,
  },
];

export function App() {
  const gatewayUrl =
    import.meta.env.VITE_GATEWAY_URL ?? 'http://localhost:4000';

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Phase 0 Workspace</p>
        <h1>SampleCRM foundation is running.</h1>
        <p className="lede">
          This frontend is intentionally small. It exists to prove the
          workspace, runtime, and service boundaries without pulling later
          phases forward.
        </p>
        <a className="gateway-link" href={gatewayUrl}>
          Gateway placeholder
        </a>
      </section>

      <section className="service-grid" aria-label="Planned services">
        {serviceCards.map((service) => (
          <article key={service.name} className="service-card">
            <p className="service-title">{service.name}</p>
            <p className="service-copy">{service.description}</p>
            <p className="service-meta">
              http://localhost:{service.port}
              {service.path}
            </p>
          </article>
        ))}
      </section>
    </main>
  );
}
