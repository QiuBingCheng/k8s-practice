這是一份為你精心整理的 Kubernetes 核心架構與網路流量診斷筆記。這份筆記專注於你今日遇到的痛點與深入探討的技術邏輯。

🚀 Kubernetes 網路與架構深度筆記
一、 流量診斷：為什麼 Port-forward 通了，外部卻不通？
這是開發 K8s 時最常遇到的「假象」。

1. 兩種連線路徑的本質區別
Port-forward (開發專線)：

路徑：你的電腦 -> K8s API Server -> Pod。

特性：它是點對點的「後門」，跳過了 Service 的負載均衡和 Ingress 的路由規則。

結論：它通了，僅代表 「容器內的程式碼 (如 FastAPI) 運作正常」，不代表網路設定正確。

Ingress/Service (正式大門)：

路徑：瀏覽器 -> Ingress -> Service -> Pod。

特性：這是生產環境的標準路徑，涉及域名解析、路徑匹配與標籤選取。

2. 404 Page Not Found 的真相
在 k3d 環境下，出現 404 通常不是程式沒開，而是 「門戶大開，但沒人接線」：

Ingress Controller (如 Traefik) 已經接到了來自 8081 的請求。

但因為你沒有定義 Ingress Resource，Traefik 找不到對應的 Service 目的地，所以回傳預設的 404。

二、 服務發現機制：Label 與 Port 的連動
我們釐清了 K8s 如何在動態環境中精準投遞流量。

1. 核心組件對照表
2. 為什麼需要 Selector？
K8s 是一組動態的 Pod 集合，Pod 可能隨時重啟並獲得新的 IP。

Service 不記 IP：它只認標籤。只要 Pod 貼著正確的標籤，Service 就會自動將其加入 Endpoints 清單。

負載均衡：當有多個 Pod 擁有相同標籤時，Service 會自動實現流量平分 (Round-Robin)。

三、 架構省思：Istio 的強大與沉重
針對你曾遇到的 OOM (Out of Memory) 事件進行的技術復盤。

1. Sidecar (Envoy) 的資源詛咒
Istio 透過在每個 Pod 旁注入一個 Sidecar 容器來接管流量，但這會帶來以下風險：

配置膨脹：預設情況下，每個 Sidecar 會儲存全叢集的服務路徑表。在大型專案中，這會導致 Sidecar 消耗極大記憶體，進而引發 OOMKilled。

解決方案：必須配置 Sidecar 資源來限制流量的可見範圍 (Egress Scope)。

2. 什麼時候該拆掉 Istio？
如果你不需要以下功能，建議回歸 「純 K8s + Ingress」：

複雜的流量切分 (如 1% 流量測試)。

跨服務的雙向 TLS 加密。

分佈式鏈路追蹤 (Tracing)。

優點：架構簡單、診斷容易、省下大筆記憶體資源。

四、 進階 Ingress：網址改寫 (Rewrite)
這是在不修改程式碼的情況下，調整外部存取路徑的神技。

1. 應用場景
當你的 FastAPI 寫的是根目錄 /，但你想讓外部透過 /docs 存取時。

2. Annotation 的魔力
外部請求：example.com/docs

轉發內部：fastapi-service/ (自動修剪掉 /docs)

價值：實現了 「基礎設施 (Ingress)」 與 「應用程式 (Code)」 的解耦。

🛠️ 今日排錯黃金流程
當網路不通時，請按此順序檢查：

Pod 層：kubectl get pods (確認是 Running) -> kubectl port-forward (確認程式能跑)。

Service 層：kubectl get ep (確認 Endpoints 欄位有抓到 Pod IP，若為 <none> 則是 Label 寫錯)。

Ingress 層：確認 rules 下的 service.name 是否正確，以及域名是否已加入電腦的 hosts。

Istio 進階筆記 流量權重與 Pod 的互動邏輯
一、 核心概念：流量 vs. 實體
在 Istio 的世界裡，「你想給多少流量 (Weight)」 與 「你開了多少個 Pod (Replicas)」 是兩件完全獨立的事情。

原生 K8s Service：按「人頭」分。Pod 越多，分到的流量比例越高。

Istio VirtualService：按「比例」分。先切好餅，再分給該組的 Pod。

二、 流量分發的「兩關卡」模型
當你設定 v1 (99%) 與 v2 (1%) 時，請求會經歷以下兩個階段：

第一關：權重抽籤 (VirtualService 層級)
執行者：發送端的 Sidecar (Envoy Proxy)。

邏輯：當請求進來，Sidecar 會產生一個隨機數進行「抽籤」。

結果：決定這筆請求屬於哪個 Subset (分組)。

案例：即便 v2 只有 1 個 Pod，只要它沒被抽中那 1% 的籤，它連 1 位客人都等不到。

第二關：組內負載均衡 (Sidecar 層級)
執行者：Sidecar (Envoy Proxy)。

觸發條件：當第一關決定該請求屬於 v2 分組，且 v2 擁有多個 Pod 時。

邏輯：Sidecar 會查看 v2 分組下的所有 Endpoint (Pod IPs)，並執行平均分配（預設為 Round Robin）。

關鍵結論：
如果 v2 只有一個 Pod：它確實會承接該分組 100% 的流量，但這份流量僅佔全系統的 1%。

如果 v2 有多個 Pod：這 1% 的總量會被平均攤分到這些 Pod 身上。

四、 為什麼要這樣設計？
解耦 (Decoupling)：你不需要為了調整流量比例而去頻繁修改 Deployment 的 replicas 數量。

精準實驗：你可以用極少的資源 (1 個 Pod) 去承接極小的流量 (0.1%)，進行最安全的線上測試。

效能觀察：你可以故意讓少數 Pod 承接不成比例的高流量，來測試程式碼在高壓下的瓶頸。