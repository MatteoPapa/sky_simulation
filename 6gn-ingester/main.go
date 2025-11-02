package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	mqtt "github.com/eclipse/paho.mqtt.golang"
	log "github.com/sirupsen/logrus"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

type UAVMessage struct {
	UavID         string  `json:"uav_id"`
	UavType       string  `json:"uav_type"`
	Latitude      float64 `json:"latitude"`
	Longitude     float64 `json:"longitude"`
	Altitude      float64 `json:"altitude"`
	Speed         float64 `json:"speed"`
	Direction     float64 `json:"direction"`
	VerticalSpeed float64 `json:"vertical_speed"`
}

type Envelope struct {
	Data []UAVMessage      `json:"data"`
	Meta map[string]string `json:"meta"`
}

func main() {
	initLogging()

	// ---- Config via envs ----
	mqttHost := getenv("MQTT_HOST", "localhost")
	mqttPort := getenv("MQTT_PORT", "1883")
	mqttTopic := getenv("MQTT_TOPIC", "updates")
	tinyfaasBase := getenv("TINYFAAS_BASE", "http://localhost:8000")
	updateURL := fmt.Sprintf("%s/update", trimSlash(tinyfaasBase))

	broker := fmt.Sprintf("tcp://%s:%s", mqttHost, mqttPort)
	log.Infof("MQTT broker: %s, topic: %s", broker, mqttTopic)
	log.Infof("tinyFaaS update URL: %s", updateURL)

	// ---- MQTT client ----
	opts := mqtt.NewClientOptions().AddBroker(broker)
	opts.SetClientID(fmt.Sprintf("ingester-%d", time.Now().UnixNano()))
	opts.SetKeepAlive(30 * time.Second)
	opts.SetConnectRetry(true)
	opts.SetConnectRetryInterval(3 * time.Second)
	opts.SetAutoReconnect(true)
	opts.OnConnect = func(c mqtt.Client) {
		log.Info("MQTT connected; subscribing…")
		if token := c.Subscribe(mqttTopic, 0, func(_ mqtt.Client, m mqtt.Message) {
			handleMessage(updateURL, m.Payload())
		}); token.Wait() && token.Error() != nil {
			log.Errorf("subscribe error: %v", token.Error())
		}
	}

	client := mqtt.NewClient(opts)
	if token := client.Connect(); token.Wait() && token.Error() != nil {
		log.Fatalf("MQTT connect error: %v", token.Error())
	}

	// graceful shutdown
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGINT, syscall.SIGTERM)
	<-sig
	log.Info("Shutting down...")
	client.Disconnect(250)
}

func handleMessage(updateURL string, payload []byte) {
	log.Debugf("MQTT msg: %s", string(payload))

	var u UAVMessage
	if err := json.Unmarshal(payload, &u); err != nil {
		log.Errorf("bad JSON on MQTT topic: %v", err)
		return
	}

	env := Envelope{
		Data: []UAVMessage{u},
		Meta: map[string]string{
			"origin":           "self_report",
			"ingest_timestamp": time.Now().UTC().Format(time.RFC3339),
		},
	}

	b, _ := json.Marshal(env)
	postUpdate(context.Background(), updateURL, b)
}

func postUpdate(_ context.Context, url string, body []byte) {
	req, err := http.NewRequest("POST", url, bytes.NewBuffer(body))
	if err != nil {
		log.Error("req build:", err)
		return
	}
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-tinyFaaS-Async", "true")

	httpClient := &http.Client{Timeout: 5 * time.Second}
	resp, err := httpClient.Do(req)
	if err != nil {
		log.Error("POST /update:", err)
		return
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusAccepted {
		log.Errorf("update -> %d (want 202)", resp.StatusCode)
	} else {
		log.Info("update -> 202 Accepted")
	}
}

func getenv(k, def string) string {
	if v := os.Getenv(k); v != "" {
		return v
	}
	return def
}
func trimSlash(s string) string {
	if s == "" {
		return s
	}
	if s[len(s)-1] == '/' {
		return s[:len(s)-1]
	}
	return s
}
func initLogging() {
	lvl, err := log.ParseLevel(getenv("LOG_LEVEL", "info"))
	if err != nil {
		lvl = log.InfoLevel
	}
	log.SetLevel(lvl)
	log.SetFormatter(&log.TextFormatter{TimestampFormat: "15:04:05.000", FullTimestamp: true})
}
