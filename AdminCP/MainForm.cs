using System.Diagnostics;
using System.Net.Http.Headers;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace SkynetShield.Admin;
public sealed partial class MainForm : Form
{
    readonly Color bg = Color.FromArgb(19, 25, 36), panel = Color.FromArgb(31, 42, 58), ink = Color.FromArgb(226, 234, 245);
    readonly TextBox endpoint = new() { Text = "http://127.0.0.1:8765", Width = 340 };
    readonly TextBox adminKey = new() { UseSystemPasswordChar = true, Width = 340 };
    readonly TextBox gameKey = new() { UseSystemPasswordChar = true, Width = 340 };
    readonly TextBox python = new() { Text = "python", Width = 340 };
    readonly TextBox root = new() { Text = Environment.CurrentDirectory, Width = 340 };
    readonly TextBox database = new() { Text = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "SkynetShield", "shield.sqlite3"), Width = 340 };
    readonly Label status = new() { Text = "Sin conectar", AutoSize = true };
    readonly Label sessions = new() { Text = "—", AutoSize = true, Font = new Font("Segoe UI", 26, FontStyle.Bold) };
    readonly Label eventsCount = new() { Text = "—", AutoSize = true, Font = new Font("Segoe UI", 26, FontStyle.Bold) };
    readonly RichTextBox console = new() { Dock = DockStyle.Fill, ReadOnly = true, Font = new Font("Consolas", 10) };
    readonly DataGridView events = new() { Dock = DockStyle.Fill, ReadOnly = true, AllowUserToAddRows = false, AllowUserToDeleteRows = false, AutoSizeColumnsMode = DataGridViewAutoSizeColumnsMode.Fill, RowHeadersVisible = false };
    readonly HttpClient http = new(new HttpClientHandler { AllowAutoRedirect = false, UseCookies = false, UseProxy = false }) { Timeout = TimeSpan.FromSeconds(8) };
    readonly System.Windows.Forms.Timer timer = new() { Interval = 15000 };
    readonly ComboBox filter = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 230 };
    readonly CancellationTokenSource lifetime = new();
    List<EventRow> rows = new();
    Process? child;
    bool busy, closing;
    sealed record EventRow(long Id, DateTimeOffset Time, string Session, string Kind, string Source, string Server);

    public MainForm()
    {
        Text = "Skynet Shield | AdminCP Enterprise V2";
        MinimumSize = new Size(960, 640); Size = new Size(1200, 790);
        StartPosition = FormStartPosition.CenterScreen;
        BackColor = bg; ForeColor = ink; Font = new Font("Segoe UI", 10);
        var tabs = new TabControl { Dock = DockStyle.Fill };
        var header = new Label { Text = "  SKYNET SHIELD   /   SECURITY OPERATIONS", Dock = DockStyle.Top, Height = 54, Font = new Font("Segoe UI", 16, FontStyle.Bold), TextAlign = ContentAlignment.MiddleLeft, BackColor = panel };
        Controls.Add(tabs); Controls.Add(header);
        var dash = Tab(tabs, "Dashboard");
        var cards = Flow(); cards.Controls.Add(Card("Sesiones vigentes", sessions)); cards.Controls.Add(Card("Eventos recientes (máx. 100)", eventsCount));
        cards.Controls.Add(Card("Estado de API", status));
        cards.Controls.Add(Button("Actualizar", async () => await RefreshAsync()));
        var automatic = new CheckBox { Text = "Actualizar cada 15 segundos", AutoSize = true };
        automatic.CheckedChanged += (_, _) => { if (automatic.Checked) timer.Start(); else timer.Stop(); };
        cards.Controls.Add(automatic); dash.Controls.Add(cards);
        timer.Tick += async (_, _) => await RefreshAsync();

        var control = Tab(tabs, "Server Control"); var controls = Flow();
        controls.Controls.Add(Button("Iniciar servidor local", StartServer));
        controls.Controls.Add(Button("Detener servidor propio", StopServer));
        controls.Controls.Add(new Label { Text = "Solo controla el proceso iniciado por esta aplicación. Servicio local de desarrollo.", AutoSize = true });
        control.Controls.Add(controls);

        BuildManagementTabs(tabs);
        var eventTab = Tab(tabs, "Security Events");
        foreach (var name in new[] {"ID","Fecha UTC","Servidor","Sesión","Tipo","Origen"}) events.Columns.Add(name,name);
        filter.Items.AddRange(new object[] {"Todos","integrity_mismatch","module_unlisted","memory_mismatch","regular_timing_review"}); filter.SelectedIndex = 0;
        filter.SelectedIndexChanged += (_, _) => RenderEvents();
        var bar = new FlowLayoutPanel { Dock = DockStyle.Top, Height = 44 };
        bar.Controls.Add(filter); bar.Controls.Add(serverFilter); bar.Controls.Add(Button("Actualizar", async () => await RefreshAsync())); bar.Controls.Add(Button("Exportar JSON", Export));
        eventTab.Controls.Add(events); eventTab.Controls.Add(bar);
        var report = Tab(tabs, "Reports"); var reportFlow = Flow();
        reportFlow.Controls.Add(Button("Exportar eventos filtrados (JSON)", Export));
        report.Controls.Add(reportFlow);
        var log = Tab(tabs, "Console"); log.Controls.Add(console);
        var config = Tab(tabs, "Settings"); var form = Flow(); form.FlowDirection = FlowDirection.TopDown; form.WrapContents = false;
        foreach (var (label, field) in new[] {("API URL",endpoint),("Admin key (64 hex)",adminKey),("GameServer key (64 hex)",gameKey),("Python executable",python),("Repository root",root),("SQLite path",database)}) {
            form.Controls.Add(new Label { Text = label, AutoSize = true }); form.Controls.Add(field);
        }
        form.Controls.Add(Button("Generar claves nuevas (desarrollo)", () => {
            adminKey.Text = Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
            gameKey.Text = Convert.ToHexString(System.Security.Cryptography.RandomNumberGenerator.GetBytes(32)).ToLowerInvariant();
            InvalidateSnapshot();
        }));
        form.Controls.Add(Button("Probar conexión", async () => await RefreshAsync()));
        config.Controls.Add(form);
        endpoint.TextChanged += (_, _) => InvalidateSnapshot();
        adminKey.TextChanged += (_, _) => InvalidateSnapshot();
        BuildToolsTabs(tabs);
        ApplyTheme(this);
        events.BackgroundColor = panel; events.GridColor = bg; events.EnableHeadersVisualStyles = false;
        events.DefaultCellStyle.BackColor = panel; events.DefaultCellStyle.ForeColor = ink;
        events.ColumnHeadersDefaultCellStyle.BackColor = bg; events.ColumnHeadersDefaultCellStyle.ForeColor = ink;
        FormClosing += (_, _) => { closing = true; timer.Stop(); lifetime.Cancel(); StopServer(); http.Dispose(); };
    }
    TabPage Tab(TabControl tabs, string name) { var tab = new TabPage(name) { BackColor = bg, ForeColor = ink }; tabs.TabPages.Add(tab); return tab; }
    FlowLayoutPanel Flow() => new() { Dock = DockStyle.Fill, Padding = new Padding(16), AutoScroll = true };
    Panel Card(string name, Control value) {
        var p = new Panel { Width = 280, Height = 110, BackColor = panel, Margin = new Padding(8) };
        p.Controls.Add(new Label { Text = name, Location = new Point(12,12), AutoSize = true });
        value.Location = new Point(12,42); p.Controls.Add(value); return p;
    }
    Button Button(string text, Action action) {
        var b = new Button { Text = text, AutoSize = true, Height = 34, FlatStyle = FlatStyle.Flat, BackColor = panel, ForeColor = ink };
        b.Click += (_, _) => action(); return b;
    }
    void ApplyTheme(Control parent) {
        foreach (Control c in parent.Controls) {
            if (c is TextBoxBase || c is ComboBox) { c.BackColor = panel; c.ForeColor = ink; }
            else if (c is Label || c is CheckBox) c.ForeColor = ink;
            ApplyTheme(c);
        }
    }
    static bool ValidKey(string s) => Regex.IsMatch(s, @"\A[0-9a-f]{64}\z");
    void InvalidateSnapshot() { rows.Clear(); ClearManagement(); sessions.Text = eventsCount.Text = "—"; status.Text = "Sin conectar"; RenderEvents(); }
    void Log(string text) {
        if (closing || IsDisposed || !IsHandleCreated) return;
        if (InvokeRequired) { try { BeginInvoke(new Action(() => Log(text))); } catch (InvalidOperationException) {} return; }
        // Never append raw child output, URLs, exception details or credentials.
        if (console.TextLength > 50000) console.Clear();
        console.AppendText($"[{DateTime.Now:HH:mm:ss}] {text}\n");
    }
    async Task RefreshAsync() {
        if (busy || closing) return;
        busy = true;
        var address = endpoint.Text; var key = adminKey.Text;
        try {
            if (!Uri.TryCreate(address, UriKind.Absolute, out var uri) ||
                !(uri.Scheme == "https" || (uri.Scheme == "http" && uri.IsLoopback)) ||
                uri.UserInfo.Length != 0 || uri.Query.Length != 0 || uri.Fragment.Length != 0 || uri.AbsolutePath != "/" || !ValidKey(key)) {
                InvalidateSnapshot(); status.Text = "Configuración inválida"; return;
            }
            using var req = new HttpRequestMessage(HttpMethod.Get, new Uri(uri,"/v1/admin/overview"));
            req.Headers.Authorization = new AuthenticationHeaderValue("Bearer",key);
            using var response = await http.SendAsync(req,HttpCompletionOption.ResponseHeadersRead,lifetime.Token);
            if (address != endpoint.Text || key != adminKey.Text || closing) return;
            if (!response.IsSuccessStatusCode) { InvalidateSnapshot(); status.Text = $"HTTP {(int)response.StatusCode}"; Log("API rechazó la consulta."); return; }
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
            deadline.CancelAfter(TimeSpan.FromSeconds(8));
            using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var buffer = new MemoryStream();
            var chunk = new byte[4096];
            int count;
            while ((count = await stream.ReadAsync(chunk.AsMemory(), deadline.Token)) != 0) {
                if (buffer.Length + count > 262144) throw new InvalidDataException();
                buffer.Write(chunk,0,count);
            }
            using var json = JsonDocument.Parse(buffer.ToArray());
            var obj = json.RootElement;
            var total = obj.GetProperty("active_sessions").GetInt32();
            if (total < 0) throw new InvalidDataException();
            var next = new List<EventRow>();
            foreach (var e in obj.GetProperty("events").EnumerateArray()) {
                if (next.Count >= 100) throw new InvalidDataException();
                next.Add(new(e.GetProperty("id").GetInt64(),
                    DateTimeOffset.FromUnixTimeSeconds((long)e.GetProperty("created").GetDouble()),
                    e.GetProperty("game_session").GetString() ?? "",e.GetProperty("kind").GetString() ?? "",e.GetProperty("source").GetString() ?? "",e.GetProperty("server_id").GetString() ?? ""));
            }
            if (closing || address != endpoint.Text || key != adminKey.Text) return;
            var snapshot = await FetchManagement(uri,key);
            if (closing || address != endpoint.Text || key != adminKey.Text) return;
            rows = next; ApplyManagement(snapshot); sessions.Text = total.ToString(); eventsCount.Text = rows.Count.ToString();
            status.Text = "Conectado"; RenderEvents(); Log("Consulta de actividad correcta.");
        } catch (Exception) { if (!closing && address == endpoint.Text && key == adminKey.Text) { InvalidateSnapshot(); status.Text = "Error de conexión o datos"; Log("No fue posible consultar la API."); } }
        finally { busy = false; }
    }
    void RenderEvents() {
        events.Rows.Clear();
        foreach (var row in FilteredEvents())
            events.Rows.Add(row.Id,row.Time.ToString("yyyy-MM-dd HH:mm:ss"),row.Server,row.Session,row.Kind,row.Source);
    }
    void Export() {
        using var dialog = new SaveFileDialog { Filter = "JSON|*.json", FileName = "shield-events.json" };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        try { File.WriteAllText(dialog.FileName,JsonSerializer.Serialize(FilteredEvents().ToArray(),new JsonSerializerOptions { WriteIndented = true })); Log("Reporte exportado."); }
        catch (Exception) { Log("No se pudo exportar el reporte."); }
    }
    void StartServer() {
        try {
            if (child is { HasExited: false }) { Log("El servidor propio ya está iniciado."); return; }
            if (!ValidKey(adminKey.Text) || !ValidKey(gameKey.Text) || adminKey.Text == gameKey.Text ||
                !File.Exists(Path.Combine(root.Text,"Server","run.py"))) { Log("Revisa claves y carpeta del repositorio."); return; }
            var db = Path.GetFullPath(database.Text);
            Directory.CreateDirectory(Path.GetDirectoryName(db)!);
            child?.Dispose(); child = null;
            var info = new ProcessStartInfo(python.Text) { WorkingDirectory = Path.GetFullPath(root.Text), UseShellExecute = false, CreateNoWindow = true, RedirectStandardOutput = true, RedirectStandardError = true };
            info.ArgumentList.Add("-u"); info.ArgumentList.Add("-m"); info.ArgumentList.Add("Server.run");
            if (registryPath.Text.Trim().Length > 0) info.Environment["SHIELD_REGISTRY"] = Path.GetFullPath(registryPath.Text);
            else info.Environment.Remove("SHIELD_REGISTRY");
            info.Environment["SHIELD_GAME_KEY"] = gameKey.Text; info.Environment["SHIELD_ADMIN_KEY"] = adminKey.Text; info.Environment["SHIELD_DB"] = db;
            child = new Process { StartInfo = info, EnableRaisingEvents = true };
            child.OutputDataReceived += (_, e) => { if (e.Data != null) Log("Servidor: mensaje recibido."); };
            child.ErrorDataReceived += (_, e) => { if (e.Data != null) Log("Servidor: diagnóstico recibido."); };
            child.Exited += (_, _) => Log("El proceso del servidor finalizó.");
            child.Start(); child.BeginOutputReadLine(); child.BeginErrorReadLine();
            Log("Proceso local iniciado; verifica conexión en Dashboard.");
        } catch (Exception) { Log("No se pudo iniciar el servidor local."); }
    }
    void StopServer() {
        if (child == null) return;
        try { if (!child.HasExited) { child.Kill(); child.WaitForExit(1000); } Log("Servidor propio detenido."); }
        catch (Exception) { Log("No se pudo detener el servidor propio."); return; }
        child.Dispose(); child = null;
    }
}
