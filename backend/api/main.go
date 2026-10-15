// GoのHTTP起動入口。内部通信の取得先を外部HTTPハンドラーへ注入する。
package main

import (
	"context"
	"errors"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"grad-checker/backend/api/presentation"
	accounts "grad-checker/backend/modules/accounts/infrastructure"
	"grad-checker/backend/modules/subjects/infrastructure"
)

func main() {
	listen := flag.String("listen", "127.0.0.1:8000", "外部APIの待受アドレス")
	pythonURL := flag.String("python-url", "http://127.0.0.1:8001", "Python内部サービスのオリジン")
	preview := flag.Bool("subject-list-preview", false, "開発用科目一覧APIを有効にする")
	origin := flag.String("public-origin", "http://127.0.0.1:5173", "認証で許可する画面のオリジン")
	flag.Parse()
	client, err := infrastructure.NewPythonSubjectListClient(*pythonURL, 5*time.Second)
	if err != nil {
		log.Fatal(err)
	}
	authClient, err := accounts.NewPythonAuthClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	profileClient, err := accounts.NewPythonProfileClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	profileHandler := presentation.NewProfileHandler(profileClient, *origin, presentation.NewSubjectListHandler(client, *preview))
	handler, err := presentation.NewAuthHandler(authClient, *origin, profileHandler)
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{Addr: *listen, Handler: handler, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	done := make(chan struct{})
	go func() {
		defer close(done)
		<-ctx.Done()
		shutdown, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		if err := server.Shutdown(shutdown); err != nil {
			log.Print(err)
		}
	}()
	log.Printf("Go API: http://%s → Python内部サービス: %s", *listen, *pythonURL)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	<-done
}
