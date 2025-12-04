"""RabbitMQ connection and messaging utilities."""
import json
import os
from typing import Any, Tuple

import pika
from dotenv import load_dotenv
from rich.console import Console

load_dotenv()

EXCHANGE_NAME = os.getenv("RABBITMQ_EXCHANGE_NAME")
EXCHANGE_TYPE = os.getenv("RABBITMQ_EXCHANGE_TYPE")
ROUTING_KEY_POSITION = os.getenv("RABBITMQ_ROUTING_KEY_POSITION")
ROUTING_KEY_TRIGGER = "RADr.Handout.Trigger"


def get_connection_parameters() -> pika.ConnectionParameters:
    """Get RabbitMQ connection parameters from environment variables."""
    username = os.getenv("RABBITMQ_USERNAME")
    password = os.getenv("RABBITMQ_PASSWORD")
    host = os.getenv("RABBITMQ_HOST")
    port_str = os.getenv("RABBITMQ_PORT")
    vhost = os.getenv("RABBITMQ_VHOST")
    
    port = int(port_str) if port_str else None
    
    credentials = pika.PlainCredentials(username, password)
    return pika.ConnectionParameters(
        host=host,
        port=port,
        virtual_host=vhost,
        credentials=credentials,
    )


def setup_rabbitmq_connection() -> Tuple[pika.BlockingConnection, Any]:
    """Set up and return RabbitMQ connection and channel."""
    connection_parameters = get_connection_parameters()
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()
    
    try:
        channel.exchange_declare(
            exchange=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE,
            durable=False
        )
    except pika.exceptions.ChannelClosedByBroker as e:
        if e.reply_code == 406:
            channel = connection.channel()
        else:
            raise
    
    return connection, channel


def send_thumb_position(channel: Any, thumb_x_normalized: float, thumb_y_normalized: float) -> None:
    """Send thumb tip position (normalized 0-1) to RabbitMQ as JSON array."""
    console = Console()
    message = json.dumps([thumb_x_normalized, thumb_y_normalized])
    
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY_POSITION,
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    console.print(f"[dim]Sent thumb position (normalized): {message} to {EXCHANGE_NAME}/{ROUTING_KEY_POSITION}[/dim]")


def send_pinch_trigger(channel: Any, is_pinching: bool) -> None:
    """Send pinch trigger state (True/False) to RabbitMQ routing key RADr.Handout.Trigger."""
    console = Console()
    message = json.dumps(is_pinching)
    
    channel.basic_publish(
        exchange=EXCHANGE_NAME,
        routing_key=ROUTING_KEY_TRIGGER,
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    console.print(f"[dim]Sent pinch trigger: {is_pinching} to {EXCHANGE_NAME}/{ROUTING_KEY_TRIGGER}[/dim]")

