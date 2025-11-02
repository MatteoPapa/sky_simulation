package main

import (
	"fmt"
	"os"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}

func main() {
	// Config (env-overridable)
	host := getenv("MQTT_HOST", "localhost")
	port := getenv("MQTT_PORT", "1883")
	topic := getenv("MQTT_TOPIC", "updates")
	qos := byte(0) // 0,1,2; change if you need at-least-once (1)

	// Broker URL
	broker := fmt.Sprintf("tcp://%s:%s", host, port)

	// MQTT client options
	opts := mqtt.NewClientOptions().
		AddBroker(broker).
		SetClientID(fmt.Sprintf("uav-pub-%d", time.Now().UnixNano())).
		SetKeepAlive(30 * time.Second).
		SetPingTimeout(10 * time.Second).
		SetConnectRetry(true).
		SetConnectRetryInterval(3 * time.Second).
		SetAutoReconnect(true)

	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		panic(token.Error())
	}
	defer client.Disconnect(250)

	// Your messages
	jsonBlocks := []string{
		`{"uav_id":"001","uav_type":"1","latitude":52.0,"longitude":0.1,"altitude":10000,"speed":50,"direction":90,"vertical_speed":0}`,
		`{"uav_id":"002","uav_type":"1","latitude":52.0,"longitude":0.2,"altitude":10000,"speed":50,"direction":270,"vertical_speed":0}`,
		`{"uav_id":"003","uav_type":"1","latitude":55.0,"longitude":0.15,"altitude":10000,"speed":50,"direction":270,"vertical_speed":0}`,
		`{"uav_id":"004","uav_type":"1","latitude":55.0,"longitude":0.25,"altitude":10000,"speed":50,"direction":90,"vertical_speed":0}`,
	}

	for i := 0; i < 4; i++ {
		payload := []byte(jsonBlocks[i%len(jsonBlocks)])
		token := client.Publish(topic, qos, false, payload)
		token.Wait() // wait for publish to complete (sync)
		if err := token.Error(); err != nil {
			fmt.Printf("Publish error: %v\n", err)
		} else {
			fmt.Printf("Published %d to %s: %s\n", i, topic, payload)
		}
		time.Sleep(1 * time.Second)
	}

	fmt.Println("Done.")
}
