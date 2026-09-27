# 公网部署说明

这个项目是 `Streamlit + SQLite` 应用，不能作为纯静态网页直接发布。GitHub 可以用来托管代码，但 GitHub Pages 不能直接运行这个网站；公网运行需要再接一个能运行 Python 服务的平台。

当前应用已经支持管理员写权限：

- 没有配置 `APP_ADMIN_PASSWORD` 时，本地默认是管理员模式。
- 配置 `APP_ADMIN_PASSWORD` 后，公网访客只能浏览。
- 新增、上传、编辑、删除、同义/同根合并、生成复习计划、复习打分等写操作需要管理员密码。

当前应用也支持 GitHub 数据库同步：

- 启动时从 GitHub 拉取最新 `gre_vocab.db`。
- 管理员新增、上传、编辑、删除或生成计划后，会把新的 `gre_vocab.db` 写回 GitHub。
- 这样 Streamlit Cloud 重启或刷新后，不会回到最初的数据库。

## 推荐方案

### 方案 A：GitHub + Streamlit Community Cloud

适合：快速分享给别人打开。

基本步骤：

1. 把本项目上传到 GitHub 仓库。
2. 在 Streamlit Community Cloud 创建应用。
3. 选择仓库、分支和入口文件：

```text
app.py
```

4. 平台会读取 `requirements.txt` 安装依赖。
5. 创建一个 GitHub token，用于让网站把更新后的 `gre_vocab.db` 写回仓库。

推荐使用 GitHub Fine-grained personal access token：

- Repository access：只选择 `leo66-lab/GREat-Leo`
- Repository permissions：`Contents` 选择 `Read and write`

6. 在 Streamlit 应用的 Secrets 里添加：

```toml
APP_ADMIN_PASSWORD = "换成你的管理员密码"
GITHUB_DB_SYNC = "true"
GITHUB_TOKEN = "换成你的 GitHub token"
GITHUB_REPO = "leo66-lab/GREat-Leo"
GITHUB_BRANCH = "main"
GITHUB_DB_PATH = "gre_vocab.db"
```

7. 部署完成后获得公网链接。

注意：

- 如果仓库是公开仓库，`gre_vocab.db` 里的词库数据也会随代码公开。需要隐藏数据时，请使用私有仓库。
- Streamlit Community Cloud 的本地文件系统不适合长期保存用户写入。本项目通过 `GITHUB_TOKEN` 把数据库同步回 GitHub，适合你自己维护、别人浏览。
- 如果很多人同时编辑，GitHub 文件同步可能发生冲突。多人长期协作建议迁移到 Render / Railway / VPS + 持久磁盘或外部数据库。

### 方案 B：Render / Railway / VPS

适合：多人长期使用、需要保存所有新增记录。

启动命令：

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port $PORT
```

如果平台不提供 `$PORT`，可以使用固定端口：

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

建议开启持久磁盘，把这些目录放在持久卷里：

```text
gre_vocab.db
exports/
backups/
```

同时配置环境变量：

```text
APP_ADMIN_PASSWORD=换成你的管理员密码
```

## 数据提醒

公开部署后，能访问链接的人可能看到你的词库内容。如果允许别人编辑，所有人会共享同一个数据库。正式公开前，建议先备份：

```powershell
copy "D:\AI培训工具\GRE_Vocabulary\gre_vocab.db" "D:\AI培训工具\GRE_Vocabulary\backups\gre_vocab_before_public.db"
```
