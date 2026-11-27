using System.Net.Http.Headers;
using System.Text.Json;
using System.Xml;
using System.Xml.Linq;
using System.Text.RegularExpressions;

namespace SkynetShield.Admin;
public sealed partial class MainForm
{
    readonly DataGridView serverGrid = MakeGrid();
    readonly DataGridView sessionGrid = MakeGrid();
    readonly ComboBox serverFilter = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 150 };
    readonly ComboBox sessionFilter = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 200 };
    readonly Label sessionNote = new() { AutoSize = true };
    readonly TextBox registryPath = new() { Width = 420 };
    readonly Label registryResult = new() { AutoSize = true };
    List<SessionInfo> sessionRows = new();
    sealed record SessionInfo(string Server,string Id,double Expires,double? Seen);
    sealed record ManagementSnapshot(List<(string Id,int Count)> Servers,List<SessionInfo> Sessions,bool Truncated);
    static DataGridView MakeGrid() => new() { Dock=DockStyle.Fill, ReadOnly=true, AllowUserToAddRows=false, AllowUserToDeleteRows=false, RowHeadersVisible=false, AutoSizeColumnsMode=DataGridViewAutoSizeColumnsMode.Fill };
    void ThemeGrid(DataGridView grid) {
        grid.BackgroundColor=panel; grid.GridColor=bg; grid.EnableHeadersVisualStyles=false;
        grid.DefaultCellStyle.BackColor=panel; grid.DefaultCellStyle.ForeColor=ink;
        grid.ColumnHeadersDefaultCellStyle.BackColor=bg; grid.ColumnHeadersDefaultCellStyle.ForeColor=ink;
    }
    void BuildManagementTabs(TabControl tabs) {
        var serversTab=Tab(tabs,"GameServers");
        serverGrid.Columns.Add("Server","GameServer ID"); serverGrid.Columns.Add("Count","Sesiones vigentes");
        var serverBar=new FlowLayoutPanel { Dock=DockStyle.Top, Height=45 };
        serverBar.Controls.Add(Button("Actualizar",async ()=>await RefreshAsync()));
        serverBar.Controls.Add(new Label { Text="Instancias registradas; no indica conexión física.", AutoSize=true });
        serversTab.Controls.Add(serverGrid); serversTab.Controls.Add(serverBar);
        var sessionsTab=Tab(tabs,"Sessions");
        foreach(var col in new[]{"Servidor","Sesión","Expira UTC","Última actividad UTC"}) sessionGrid.Columns.Add(col,col);
        var bar=new FlowLayoutPanel { Dock=DockStyle.Top, Height=65 };
        bar.Controls.Add(sessionFilter); bar.Controls.Add(Button("Actualizar",async ()=>await RefreshAsync())); bar.Controls.Add(sessionNote);
        sessionsTab.Controls.Add(sessionGrid); sessionsTab.Controls.Add(bar);
        serverFilter.Items.Add("Todos"); serverFilter.SelectedIndex=0;
        sessionFilter.Items.Add("Todos"); sessionFilter.SelectedIndex=0;
        serverFilter.SelectedIndexChanged+=(_,_)=>RenderEvents();
        sessionFilter.SelectedIndexChanged+=(_,_)=>RenderSessions();
        ThemeGrid(serverGrid); ThemeGrid(sessionGrid);
    }
    async Task<JsonDocument> ReadAdmin(Uri uri,string key,string route) {
        using var deadline=CancellationTokenSource.CreateLinkedTokenSource(lifetime.Token);
        deadline.CancelAfter(TimeSpan.FromSeconds(8));
        using var req=new HttpRequestMessage(HttpMethod.Get,new Uri(uri,route));
        req.Headers.Authorization=new AuthenticationHeaderValue("Bearer",key);
        using var response=await http.SendAsync(req,HttpCompletionOption.ResponseHeadersRead,deadline.Token);
        response.EnsureSuccessStatusCode();
        using var stream=await response.Content.ReadAsStreamAsync(deadline.Token);
        using var data=new MemoryStream();
        byte[] chunk=new byte[4096]; int n;
        while((n=await stream.ReadAsync(chunk.AsMemory(),deadline.Token))!=0) {
            if(data.Length+n>262144) throw new InvalidDataException();
            data.Write(chunk,0,n);
        }
        return JsonDocument.Parse(data.ToArray());
    }
    async Task<ManagementSnapshot> FetchManagement(Uri uri,string key) {
        using var servers=await ReadAdmin(uri,key,"/v1/admin/servers");
        using var sessions=await ReadAdmin(uri,key,"/v1/admin/sessions");
        var a=new List<(string Id,int Count)>(); var b=new List<SessionInfo>();
        foreach(var x in servers.RootElement.GetProperty("servers").EnumerateArray()) {
            if(a.Count>=128) throw new InvalidDataException();
            a.Add((x.GetProperty("server_id").GetString()??"",x.GetProperty("active_sessions").GetInt32()));
        }
        foreach(var x in sessions.RootElement.GetProperty("sessions").EnumerateArray()) {
            if(b.Count>=500) throw new InvalidDataException();
            var seen=x.GetProperty("last_seen");
            b.Add(new(x.GetProperty("server_id").GetString()??"",x.GetProperty("game_session").GetString()??"",
                x.GetProperty("expires").GetDouble(),seen.ValueKind==JsonValueKind.Null?null:seen.GetDouble()));
        }
        return new(a,b,sessions.RootElement.GetProperty("truncated").GetBoolean());
    }
    void UpdateFilter(ComboBox box,IEnumerable<string> ids) {
        var selected=box.SelectedItem?.ToString();
        box.Items.Clear(); box.Items.Add("Todos");
        foreach(var id in ids.Distinct().OrderBy(x=>x)) box.Items.Add(id);
        box.SelectedIndex=selected!=null&&box.Items.Contains(selected)?box.Items.IndexOf(selected):0;
    }
    void ApplyManagement(ManagementSnapshot snapshot) {
        serverGrid.Rows.Clear();
        foreach(var item in snapshot.Servers) serverGrid.Rows.Add(item.Id,item.Count);
        sessionRows=snapshot.Sessions;
        UpdateFilter(serverFilter,snapshot.Servers.Select(x=>x.Id).Concat(rows.Select(x=>x.Server)));
        UpdateFilter(sessionFilter,snapshot.Servers.Select(x=>x.Id));
        sessionNote.Text=snapshot.Truncated?"Primeras 500 sesiones; listado parcial.":"Sesiones vigentes; no equivale a jugadores online.";
        RenderSessions();
    }
    void ClearManagement() {
        serverGrid.Rows.Clear(); sessionRows.Clear(); sessionGrid.Rows.Clear(); sessionNote.Text="";
        UpdateFilter(serverFilter,Array.Empty<string>()); UpdateFilter(sessionFilter,Array.Empty<string>());
    }
    IEnumerable<EventRow> FilteredEvents() => rows.Where(r=>(filter.SelectedIndex<=0||r.Kind==filter.SelectedItem?.ToString())&&(serverFilter.SelectedIndex<=0||r.Server==serverFilter.SelectedItem?.ToString()));
    static string Utc(double value)=>DateTimeOffset.FromUnixTimeSeconds((long)value).ToString("yyyy-MM-dd HH:mm:ss");
    void RenderSessions() {
        sessionGrid.Rows.Clear();
        foreach(var row in sessionRows.Where(r=>sessionFilter.SelectedIndex<=0||r.Server==sessionFilter.SelectedItem?.ToString()))
            sessionGrid.Rows.Add(row.Server,row.Id,Utc(row.Expires),row.Seen.HasValue?Utc(row.Seen.Value):"Sin actividad");
    }
    void BuildToolsTabs(TabControl tabs) {
        var config=Tab(tabs,"Configuration"); var flow=Flow();
        flow.Controls.Add(new Label {Text="Registro XML (opcional; claves heredadas del entorno)",AutoSize=true});
        flow.Controls.Add(registryPath);
        flow.Controls.Add(Button("Seleccionar XML",()=>{using var d=new OpenFileDialog {Filter="XML|*.xml"};if(d.ShowDialog(this)==DialogResult.OK)registryPath.Text=d.FileName;}));
        flow.Controls.Add(Button("Validar registro",ValidateXml)); flow.Controls.Add(registryResult);
        config.Controls.Add(flow);
        var anti=Tab(tabs,"Anti-Macro"); var af=Flow();
        af.Controls.Add(new Label {Text="Eventos de regularidad temporal: solo revisión, no sanción. La política activa todavía se configura en código.",AutoSize=true});
        af.Controls.Add(Button("Consultar reportes Anti-Macro",()=>{filter.SelectedItem="regular_timing_review";tabs.SelectedTab=tabs.TabPages.Cast<TabPage>().First(t=>t.Text=="Security Events");}));
        anti.Controls.Add(af);
        var integrity=Tab(tabs,"Integrity"); var inf=Flow();
        inf.Controls.Add(new Label {Text="Consultar informes de integridad. La firma y verificación de manifiestos sigue en Tools/integrity.py.",AutoSize=true});
        inf.Controls.Add(Button("Consultar informes",()=>{filter.SelectedItem="integrity_mismatch";tabs.SelectedTab=tabs.TabPages.Cast<TabPage>().First(t=>t.Text=="Security Events");}));
        integrity.Controls.Add(inf);
        var db=Tab(tabs,"Database"); var df=Flow();
        var info=new Label {AutoSize=true}; df.Controls.Add(Button("Información local",()=>{
            try {var f=new FileInfo(database.Text);info.Text=f.Exists?$"SQLite local: {f.Length:N0} bytes.":"Archivo no encontrado."; }catch{info.Text="Ruta inválida.";}
        })); df.Controls.Add(info); df.Controls.Add(new Label{Text="No se realizan escrituras, compactaciones ni copias de una base activa.",AutoSize=true}); db.Controls.Add(df);
    }
    void ValidateXml() {
        try {
            var bytes=new FileInfo(registryPath.Text).Length;
            if(bytes>32768)throw new InvalidDataException();
            using var reader=XmlReader.Create(registryPath.Text,new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=32768});
            var doc=XDocument.Load(reader);var root=doc.Root;
            if(root==null||root.Name!="ShieldServers"||root.Attributes().Count()!=1||(string?)root.Attribute("version")!="1")throw new InvalidDataException();
            var ids=new HashSet<string>();var keys=new HashSet<string>();int count=0;
            foreach(var e in root.Elements()) {
                string id=(string?)e.Attribute("id")??"",key=(string?)e.Attribute("keyEnv")??"";
                if(e.Name!="Server"||e.Attributes().Count()!=2||e.HasElements||!Regex.IsMatch(id,@"\A[A-Za-z0-9_-]{1,64}\z")||!Regex.IsMatch(key,@"\ASHIELD_GAME_KEY(?:_[A-Z0-9_]+)?\z")||!ids.Add(id)||!keys.Add(key)||++count>128)throw new InvalidDataException();
            }
            if(count==0)throw new InvalidDataException();
            registryResult.Text=$"Estructura válida: {count} instancias. El servidor valida las credenciales al iniciar.";
        }catch{registryResult.Text="Registro inválido o inaccesible.";}
    }
}
