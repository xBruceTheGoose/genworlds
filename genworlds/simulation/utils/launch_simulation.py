from genworlds.simulation.simulation import Simulation


def launch_simulation(simulation: Simulation, host: str = "127.0.0.1", port: int = 7456):
    """Launch a simulation on the given host/port."""
    simulation.launch(host=host, port=port)
