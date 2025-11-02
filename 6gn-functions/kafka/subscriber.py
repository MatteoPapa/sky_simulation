from confluent_kafka import Consumer, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from datetime import datetime

HOST = "localhost"
def create_topic(topic_name):
    admin_client = AdminClient({'bootstrap.servers': f'{HOST}:9092'})   #NOTE: hardcoded credentials
    topic = NewTopic(topic_name, num_partitions=1, replication_factor=1)
    admin_client.create_topics([topic])

def create_consumer():
    conf = {'bootstrap.servers': f"{HOST}:9092", 'group.id': "group1", 'auto.offset.reset': 'earliest'}
    consumer = Consumer(conf)
    return consumer

def listen_for_messages(consumer):
    consumer.subscribe(['releases'])

    try:
        while True:
            msg = consumer.poll(60.0)

            if msg is None:
                continue
            if msg.error():
                raise KafkaException(msg.error())
            else:
                timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                print(f'[{timestamp}] '+'Received message: {}'.format(msg.value().decode('utf-8')))

    except KeyboardInterrupt:
        pass

    finally:
        consumer.close()

if __name__ == "__main__":
    create_topic('releases')
    consumer = create_consumer()
    listen_for_messages(consumer)