// GoのHTTP起動入口。ブリッジ通信の取得先を外部HTTPハンドラーへ注入する。
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

	"grad-checker/backend/apps/api/controllers"
	accounts "grad-checker/backend/modules/accounts/infrastructure/external_services"
	grades "grad-checker/backend/modules/grades/infrastructure/external_services"
	requirements "grad-checker/backend/modules/requirements/infrastructure/external_services"
	"grad-checker/backend/modules/subjects/infrastructure/external_services"
)

func main() {
	listen := flag.String("listen", "127.0.0.1:8000", "外部APIの待受アドレス")
	pythonURL := flag.String("python-url", "http://127.0.0.1:8001", "Pythonサービスのオリジン")
	preview := flag.Bool("subject-list-preview", false, "開発用科目一覧APIを有効にする")
	docs := flag.Bool("api-docs", false, "開発用のOpenAPIとSwagger UIを有効にする")
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
	gradeClient, err := grades.NewPythonGradeClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	courseClient, err := infrastructure.NewPythonCourseCatalogClient(*pythonURL, 5*time.Second)
	if err != nil {
		log.Fatal(err)
	}
	courseHandler := controllers.NewCourseHandler(courseClient, controllers.NewSubjectListHandler(client, *preview))
	gradeHandler := controllers.NewGradeHandler(gradeClient, *origin, courseHandler)
	evaluationClient, err := requirements.NewPythonEvaluationClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	checkClient, err := requirements.NewPythonCheckClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	checkHandler := controllers.NewCheckHandler(checkClient, *origin, gradeHandler)
	evaluationHandler := controllers.NewEvaluationHandler(evaluationClient, checkHandler)
	dashboardClient, err := requirements.NewPythonDashboardClient(*pythonURL)
	if err != nil {
		log.Fatal(err)
	}
	dashboardHandler := controllers.NewDashboardHandler(dashboardClient, evaluationHandler)
	profileHandler := controllers.NewProfileHandler(profileClient, *origin, dashboardHandler)
	handler, err := controllers.NewAuthHandler(authClient, *origin, profileHandler)
	if err != nil {
		log.Fatal(err)
	}
	server := &http.Server{Addr: *listen, Handler: controllers.NewAPIDocsHandler(*docs, handler), ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 15 * time.Second, IdleTimeout: 60 * time.Second}
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
	log.Printf("Go API: http://%s → Pythonサービス: %s", *listen, *pythonURL)
	if err := server.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		log.Fatal(err)
	}
	<-done
}
