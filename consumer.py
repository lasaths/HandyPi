"""RabbitMQ consumer for testing pinch trigger messages."""
import json
from typing import Any

import pika
from rich.console import Console

from rabbitmq import (
    EXCHANGE_NAME,
    ROUTING_KEY_POSITION,
    ROUTING_KEY_TRIGGER,
    setup_rabbitmq_connection,
)


def handle_trigger_message(
    channel: Any,
    method: Any,
    properties: Any,
    body: bytes,
) -> None:
    """Callback to handle pinch trigger messages."""
    console = Console()
    message = body.decode('utf-8')
    try:
        trigger_state = json.loads(message)
        if isinstance(trigger_state, bool):
            status = "[green]True (PINCHED)[/green]" if trigger_state else "[red]False (NOT PINCHED)[/red]"
            console.print(f'[green]✓[/green] Received pinch trigger: {status}')
        else:
            console.print(f'[yellow]⚠[/yellow] Invalid boolean format: {trigger_state}')
    except (ValueError, json.JSONDecodeError) as e:
        console.print(f'[red]✗[/red] Failed to parse trigger message "{message}": {e}')


def handle_position_message(
    channel: Any,
    method: Any,
    properties: Any,
    body: bytes,
) -> None:
    """Callback to handle position messages."""
    console = Console()
    message = body.decode('utf-8')
    try:
        position = json.loads(message)
        if isinstance(position, list) and len(position) == 2:
            x, y = position[0], position[1]
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                console.print(f'[cyan]✓[/cyan] Received position: x=[yellow]{x:.3f}[/yellow], y=[yellow]{y:.3f}[/yellow]')
            else:
                console.print(f'[yellow]⚠[/yellow] Invalid position format: {position}')
        else:
            console.print(f'[yellow]⚠[/yellow] Invalid position array format: {position}')
    except (ValueError, json.JSONDecodeError) as e:
        console.print(f'[red]✗[/red] Failed to parse position message "{message}": {e}')


def start_consuming(connection: pika.BlockingConnection, channel: Any) -> None:
    """Start consuming messages from RabbitMQ."""
    console = Console()
    
    trigger_queue_declare = channel.queue_declare(queue='', exclusive=True)
    trigger_queue_name = trigger_queue_declare.method.queue
    
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=trigger_queue_name,
        routing_key=ROUTING_KEY_TRIGGER
    )
    
    position_queue_declare = channel.queue_declare(queue='', exclusive=True)
    position_queue_name = position_queue_declare.method.queue
    
    channel.queue_bind(
        exchange=EXCHANGE_NAME,
        queue=position_queue_name,
        routing_key=ROUTING_KEY_POSITION
    )
    
    console.print(f'[cyan]Waiting for messages on exchange "{EXCHANGE_NAME}":[/cyan]')
    console.print(f'  [dim]- Trigger:[/dim] {ROUTING_KEY_TRIGGER}')
    console.print(f'  [dim]- Position:[/dim] {ROUTING_KEY_POSITION}')
    console.print('[dim]Press CTRL+C to exit[/dim]')
    
    channel.basic_consume(
        queue=trigger_queue_name,
        auto_ack=True,
        on_message_callback=handle_trigger_message
    )
    
    channel.basic_consume(
        queue=position_queue_name,
        auto_ack=True,
        on_message_callback=handle_position_message
    )
    
    channel.start_consuming()


if __name__ == '__main__':
    console = Console()
    connection = None
    try:
        connection, channel = setup_rabbitmq_connection()
        console.print("[green]✓[/green] Connected to RabbitMQ")
        start_consuming(connection, channel)
        
    except KeyboardInterrupt:
        console.print('\n[yellow]Consumer stopped by user[/yellow]')
        if connection and not connection.is_closed:
            connection.close()
    except Exception as e:
        console.print(f'[red]Error: {e}[/red]')
        if connection and not connection.is_closed:
            connection.close()

