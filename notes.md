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