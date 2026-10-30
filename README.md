# CCF 靜態官網

官網已轉成 HTML／CSS／JavaScript。首頁、產品頁、版型與原本樣式沿用；瀏覽網站不需要 Python、Flask、資料庫或管理後台。

- `docs/`：可直接發佈到 GitHub Pages 的完成檔案。
- `site/content.json`：中文版文案、公司資訊、產品、FAQ。
- `site/content.en.json`：英文版文案；未重複的共用設定由中文版繼承。兩種語言的產品與列表順序需保持一致。
- `site/templates/`：原本的公開頁面版型，改成靜態連結。
- `site/assets/`：樣式、圖片、表單 JavaScript。
- `site/config.json`：Formspree 表單接收網址與正式網站網址，**只放公開設定**。

## 本機預覽與更新

已附建置好的 `docs/`，上傳時不必安裝任何套件。之後修改 `site/` 的內容或圖片，再執行：

```powershell
python -m pip install -r requirements-static.txt
python scripts/build_static.py
python -m http.server 8088 --directory docs
```

開啟 `http://localhost:8088`，也可以雙擊 `preview-static.bat` 預覽。更新時一起提交 `site/` 和重新產生的 `docs/`。Python 只用於本機產生 HTML，不用部署到主機。也可以直接改 `docs/`，但下次建置會被 `site/` 的內容覆蓋。

使用 VS Code Live Server 時，對 **`docs/index.html`** 按右鍵 → Open with Live Server。`site/templates/` 是建置用範本，不能直接當網站開啟。

中文版維持原網址；英文版入口是 `docs/en/index.html`，正式網址為 `https://ccf-software.com/en/`。每頁導覽列的「中文／EN」可切換至同一頁的另一個語言版本，包含四個產品頁。兩版顯示相同的新台幣價格，英文不換算美元。修改文案或價格時，請同步更新兩份內容檔後重新建置。

## Google Analytics

已在共用版型加入 GA4 `G-NL9WDQ47C9`，中英文共十個頁面都載入一次 Google tag。程式不額外將表單姓名、電話／LINE ID 或需求內容傳給 GA。部署更新後可在 GA 的即時報表確認瀏覽資料；本機檢查只驗證追蹤碼存在，不代表已驗證 GA 帳號收件。

## GitHub Pages

1. 建立 GitHub 儲存庫，上傳這份專案（使用 Git 時 `.gitignore` 會排除本機資料庫、密鑰與快取）。
2. Settings → Pages → Build and deployment → Source 選 **Deploy from a branch**。
3. Branch 選儲存網站的分支，例如 `main`，資料夾選 **`/docs`**，儲存。
4. 網址通常是 `https://帳號.github.io/儲存庫名稱/`。使用相對路徑，支援子目錄與自訂網域。

不要把舊版 `data/`、`secret.key` 或諮詢資料上傳。使用網頁拖拉上傳時 `.gitignore` 不會自動過濾，最簡單是只上傳 `docs/` **裡面的檔案與資料夾** 到儲存庫根目錄，Pages 改選 `/(root)`；但這種方式不包含可編輯來源。

公開儲存庫內的所有已提交檔案都可被下載，**Pages 選 `/docs` 不會隱藏儲存庫的其他檔案**。`.gitignore` 只防止 Git 新增忽略檔案，不會移除已提交的內容或歷史紀錄。若曾提交真正的 Token／密鑰，應先撤銷或更換，再處理歷史紀錄。依 [GitHub 官方說明](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)，GitHub Free 的 Pages 使用公開儲存庫；GitHub Pro／Team 等支援從私人儲存庫發佈。私人原始碼儲存庫也無法隱藏送到瀏覽器的 HTML、JavaScript 與設定。本方案只需公開的 Formspree 收件網址，不需要把 API Key、Telegram Token 或登入密碼放入網站。

## 開通 Formspree 諮詢表單與 Telegram 通知

架構：GitHub Pages → Formspree → Email／Telegram 通知。不需要 Cloudflare Worker、自建後端或自己的 Telegram Bot。

**目前已填入正式 Form Endpoint：`https://formspree.io/f/mqpplkzk`。發佈後仍需實際提交測試，確認 Formspree 收件與 Telegram 通知設定。LINE 按鈕仍可使用。**

1. 到 [Formspree](https://formspree.io/) 註冊並驗證收件信箱，建立一份表單。
2. 在該表單的 Integration 頁面複製 **Form Endpoint**（格式為 `https://formspree.io/f/你的表單ID`）。這是公開收件網址，可以放在靜態網站，不是管理 API Key。
3. 在 `site/config.json` 填入：

   ```json
   {
     "contactEndpoint": "https://formspree.io/f/YOUR_FORM_ID",
     "siteUrl": "https://YOUR-ACCOUNT.github.io/YOUR-REPO"
   }
   ```

   將 `YOUR_FORM_ID` 換成真正的 ID；建置會檢查網址格式，不能保留佔位字。`siteUrl` 包含儲存庫路徑，用於分享預覽圖的完整網址；沒設定分享圖片時可留空。
4. 在 Formspree 表單的 **Workflow → Actions → Add New → Telegram** 連結你的 Telegram 帳號，依 Telegram 訊息確認登入（舊介面入口為 Plugins）。通知由 Formspree 的 Bot 傳送，無須提供自己的 Bot Token 或 Chat ID。此操作需由帳號持有人完成。
5. 執行 `python scripts/build_static.py`，將更新後的 `docs/` 上傳 GitHub。
6. 在正式官網填一筆測試諮詢，確認 Formspree 後台、Email 與 Telegram 收到稱呼、電話／LINE、需求。若 Formspree 啟用額外 CAPTCHA 驗證，需一併設定相容的表單驗證流程並實測。

表單在按鈕下方顯示傳送中、成功或失敗狀態；成功會自動捲到綠色提示並將按鈕改為「已送出 ✓」。使用 Formspree 的 `_gotcha` 隱藏陷阱欄位，防垃圾訊息、收件限制與通知由 Formspree 管理。成功表示 Formspree 已接受提交，不代表 Telegram 已送達或已讀；失敗保留輸入內容供重試或改用 LINE。客戶資料會經過 Formspree 處理與儲存，Telegram 通知需另外在其後台啟用。

目前官方文件列出的免費額度為每月 50 次提交、30 天提交紀錄；以你帳號顯示的方案為準。[官方額度說明](https://help.formspree.io/articles/account-management/account-limits)

## 驗證

```powershell
python scripts/check_static.py
node --test tests/contact-form.test.mjs
```

舊 Flask 後端、管理後台範本、資料搬移工具與啟動腳本已清除。`data/` 內仍有 2 筆舊版諮詢紀錄，先保留於本機，不能上傳公開儲存庫。`webapp/` 若仍存在，只剩未使用的舊圖片或快取，已由 `.gitignore` 排除。

參考：[Formspree HTML 表單](https://help.formspree.io/articles/building-your-form/building-an-html-form)、[Telegram 通知設定](https://help.formspree.io/articles/plugins/use-telegram-to-receive-messages/)、[隱藏陷阱欄位](https://help.formspree.io/articles/building-your-form/honeypot-spam-filtering)。
