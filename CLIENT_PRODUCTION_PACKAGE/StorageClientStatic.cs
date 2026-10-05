using System;
using System.IO;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using System.Collections.Generic;

namespace WindowsStorageMonitor
{
    class Program
    {
        private const string DEFAULT_SERVER = "http://localhost:8080";
        private const int INTERVAL_SECONDS = 10;

        // URL completo dell'endpoint di report, risolto all'avvio
        private static string reportUrl;

        // Ordine di ricerca dell'indirizzo del server:
        //   1) primo argomento da riga di comando
        //   2) variabile d'ambiente STORAGE_MONITOR_URL
        //   3) server_url.txt accanto all'eseguibile
        //   4) %LOCALAPPDATA%\WindowsStorageMonitor\server_url.txt
        //   5) http://localhost:8080
        static string ResolveServerUrl(string[] args)
        {
            string url = null;
            if (args.Length > 0) url = args[0];
            if (string.IsNullOrEmpty(url)) url = Environment.GetEnvironmentVariable("STORAGE_MONITOR_URL");
            if (string.IsNullOrEmpty(url)) url = ReadConfigFile(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "server_url.txt"));
            if (string.IsNullOrEmpty(url))
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                url = ReadConfigFile(Path.Combine(localAppData, "WindowsStorageMonitor", "server_url.txt"));
            }
            if (string.IsNullOrEmpty(url)) url = DEFAULT_SERVER;
            return url.Trim().TrimEnd('/');
        }

        static string ReadConfigFile(string path)
        {
            try
            {
                if (File.Exists(path)) return File.ReadAllText(path).Trim();
            }
            catch (Exception) { }
            return null;
        }

        static void Main(string[] args)
        {
            reportUrl = ResolveServerUrl(args) + "/api/report";

            // Esecuzione continua in background, nessuna finestra
            while (true)
            {
                SendReport();
                Thread.Sleep(INTERVAL_SECONDS * 1000);
            }
        }

        static void SendReport()
        {
            try
            {
                string hostname = Environment.MachineName;
                string localIp = GetLocalIPAddress();
                string osName = "Windows 11";
                string username = Environment.UserDomainName + "\\" + Environment.UserName;

                List<string> driveJsonList = new List<string>();

                foreach (DriveInfo drive in DriveInfo.GetDrives())
                {
                    if (drive.IsReady && drive.DriveType == DriveType.Fixed)
                    {
                        double totalGb = Math.Round((double)drive.TotalSize / (1024.0 * 1024.0 * 1024.0), 2);
                        double freeGb  = Math.Round((double)drive.AvailableFreeSpace / (1024.0 * 1024.0 * 1024.0), 2);
                        double usedGb  = Math.Round(totalGb - freeGb, 2);
                        double pctUsed = totalGb > 0 ? Math.Round((usedGb / totalGb) * 100.0, 1) : 0;

                        string driveName = drive.Name.Replace("\\", "");
                        string label = string.IsNullOrEmpty(drive.VolumeLabel) ? "Disco Locale" : drive.VolumeLabel;

                        string dJson = "{"
                            + "\"drive\":\""   + EscapeJson(driveName) + "\","
                            + "\"label\":\""   + EscapeJson(label)     + "\","
                            + "\"total_gb\":"  + totalGb.ToString(System.Globalization.CultureInfo.InvariantCulture) + ","
                            + "\"used_gb\":"   + usedGb.ToString(System.Globalization.CultureInfo.InvariantCulture)  + ","
                            + "\"free_gb\":"   + freeGb.ToString(System.Globalization.CultureInfo.InvariantCulture)  + ","
                            + "\"percent_used\":" + pctUsed.ToString(System.Globalization.CultureInfo.InvariantCulture)
                            + "}";

                        driveJsonList.Add(dJson);
                    }
                }

                // Cartelle critiche / spazzatura
                List<string> bloatJsonList = new List<string>();
                AddBloatFolder(bloatJsonList, "Temp Utente (%TEMP%)", Path.GetTempPath());
                AddBloatFolder(bloatJsonList, "Temp di Sistema",      @"C:\Windows\Temp");
                AddBloatFolder(bloatJsonList, "Cestino (Recycle Bin)", @"C:\$Recycle.Bin");
                AddBloatFolder(bloatJsonList, "Cache Windows Update",  @"C:\Windows\SoftwareDistribution\Download");
                AddBloatFolder(bloatJsonList, "File di Log Windows",   @"C:\Windows\Logs");

                string drivesArrayJson = "[" + string.Join(",", driveJsonList.ToArray()) + "]";
                string bloatArrayJson  = "[" + string.Join(",", bloatJsonList.ToArray())  + "]";

                string payload = "{"
                    + "\"hostname\":\""    + EscapeJson(hostname) + "\","
                    + "\"ip\":\""         + EscapeJson(localIp)  + "\","
                    + "\"os\":\""         + EscapeJson(osName)   + "\","
                    + "\"username\":\""   + EscapeJson(username) + "\","
                    + "\"drives\":"       + drivesArrayJson + ","
                    + "\"bloat_folders\":" + bloatArrayJson
                    + "}";

                using (WebClient client = new WebClient())
                {
                    client.Headers[HttpRequestHeader.ContentType] = "application/json";
                    client.Encoding = Encoding.UTF8;
                    client.UploadString(reportUrl, "POST", payload);
                }
            }
            catch { }
        }

        static void AddBloatFolder(List<string> list, string name, string path)
        {
            try
            {
                double sizeMb = GetDirectorySizeMB(path, 0);
                string json = "{"
                    + "\"name\":\""    + EscapeJson(name) + "\","
                    + "\"path\":\""    + EscapeJson(path) + "\","
                    + "\"size_mb\":"   + sizeMb.ToString(System.Globalization.CultureInfo.InvariantCulture)
                    + "}";
                list.Add(json);
            }
            catch { }
        }

        static double GetDirectorySizeMB(string dirPath, int depth)
        {
            long bytes = GetDirectorySizeBytes(dirPath, depth);
            return Math.Round((double)bytes / (1024.0 * 1024.0), 2);
        }

        static long GetDirectorySizeBytes(string dirPath, int depth)
        {
            if (depth > 5 || string.IsNullOrEmpty(dirPath) || !Directory.Exists(dirPath)) return 0;
            long totalBytes = 0;

            try
            {
                DirectoryInfo di = new DirectoryInfo(dirPath);

                FileInfo[] files = null;
                try { files = di.GetFiles(); } catch { }

                if (files != null)
                {
                    foreach (FileInfo fi in files)
                    {
                        try { totalBytes += fi.Length; } catch { }
                    }
                }

                DirectoryInfo[] subDirs = null;
                try { subDirs = di.GetDirectories(); } catch { }

                if (subDirs != null)
                {
                    foreach (DirectoryInfo subDi in subDirs)
                    {
                        try { totalBytes += GetDirectorySizeBytes(subDi.FullName, depth + 1); } catch { }
                    }
                }
            }
            catch { }

            return totalBytes;
        }

        static string GetLocalIPAddress()
        {
            try
            {
                using (Socket socket = new Socket(AddressFamily.InterNetwork, SocketType.Dgram, 0))
                {
                    socket.Connect("8.8.8.8", 65530);
                    IPEndPoint endPoint = socket.LocalEndPoint as IPEndPoint;
                    if (endPoint != null) return endPoint.Address.ToString();
                }
            }
            catch { }

            try
            {
                IPHostEntry host = Dns.GetHostEntry(Dns.GetHostName());
                foreach (IPAddress ip in host.AddressList)
                {
                    if (ip.AddressFamily == AddressFamily.InterNetwork && !ip.ToString().StartsWith("127."))
                        return ip.ToString();
                }
            }
            catch { }

            return "127.0.0.1";
        }

        static string EscapeJson(string s)
        {
            if (string.IsNullOrEmpty(s)) return "";
            return s.Replace("\\", "\\\\").Replace("\"", "\\\"");
        }
    }
}
