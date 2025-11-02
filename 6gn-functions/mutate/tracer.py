class TracerInitializer:
    def __init__(self, name):
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider, sampling
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource

        host = "172.17.0.1"
        port = 4317
        trace.set_tracer_provider(TracerProvider(
            resource=Resource(attributes={"service.name": name}),
            sampler=sampling.ALWAYS_ON
        ))
        trace.get_tracer_provider().add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=f"http://{host}:{port}", insecure=True))  # Force plaintext instead of SSL/TLS
            # BatchSpanProcessor(ConsoleSpanExporter())
        )

        self.tracer = trace.get_tracer(__name__)
