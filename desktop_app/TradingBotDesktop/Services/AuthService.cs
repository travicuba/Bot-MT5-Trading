using System.Net.Http;
using System.Net.Http.Json;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace TradingBotDesktop.Services;

// ── DTOs ──────────────────────────────────────────────────────────────────────

public record LoginRequest(string email, string password);
public record RegisterRequest(string first_name, string last_name, string email, string password);

public class TokenResponse
{
    [JsonPropertyName("access_token")]   public string  AccessToken   { get; set; } = "";
    [JsonPropertyName("token_type")]     public string  TokenType     { get; set; } = "bearer";
    [JsonPropertyName("user_id")]        public int     UserId        { get; set; }
    [JsonPropertyName("is_admin")]       public bool    IsAdmin       { get; set; }
    [JsonPropertyName("first_name")]     public string  FirstName     { get; set; } = "";
    [JsonPropertyName("last_name")]      public string  LastName      { get; set; } = "";
    [JsonPropertyName("email")]          public string  Email         { get; set; } = "";
    [JsonPropertyName("license_type")]   public string  LicenseType   { get; set; } = "free";
    [JsonPropertyName("license_active")] public bool    LicenseActive { get; set; }
}

public class AuthResult
{
    public bool   Success      { get; set; }
    public string? ErrorMessage { get; set; }
}

// ── Service ───────────────────────────────────────────────────────────────────

public class AuthService
{
    // Currently authenticated user info (set after login)
    public string  Token        { get; private set; } = "";
    public int     UserId       { get; private set; }
    public bool    IsAdmin      { get; private set; }
    public string  FirstName    { get; private set; } = "";
    public string  LastName     { get; private set; } = "";
    public string  Email        { get; private set; } = "";
    public string  LicenseType  { get; private set; } = "free";
    public bool    LicenseActive { get; private set; }
    public bool    IsLoggedIn   => !string.IsNullOrEmpty(Token);
    public string  FullName     => $"{FirstName} {LastName}".Trim();

    private static readonly HttpClient _http = new() { Timeout = TimeSpan.FromSeconds(15) };
    private static readonly JsonSerializerOptions _jOpt = new() { PropertyNameCaseInsensitive = true };

    private string ServerBase => AppSettings.Instance.ServerUrl.TrimEnd('/');

    // ── LOGIN ──────────────────────────────────────────────────────────────

    public async Task<AuthResult> LoginAsync(string email, string password)
    {
        try
        {
            var req = new LoginRequest(email, password);
            var response = await _http.PostAsJsonAsync($"{ServerBase}/auth/login", req);
            var body = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
            {
                var token = JsonSerializer.Deserialize<TokenResponse>(body, _jOpt);
                if (token != null)
                {
                    ApplyToken(token);
                    PersistSession();
                    return new AuthResult { Success = true };
                }
            }

            var errMsg = TryParseError(body);
            return new AuthResult { Success = false, ErrorMessage = errMsg };
        }
        catch (TaskCanceledException)
        {
            return new AuthResult { Success = false, ErrorMessage = "Tiempo de espera agotado. Revisa la URL del servidor." };
        }
        catch (Exception ex)
        {
            return new AuthResult { Success = false, ErrorMessage = $"No se pudo conectar: {ex.Message}" };
        }
    }

    // ── REGISTER ───────────────────────────────────────────────────────────

    public async Task<AuthResult> RegisterAsync(string firstName, string lastName, string email, string password)
    {
        if (string.IsNullOrWhiteSpace(firstName) || string.IsNullOrWhiteSpace(lastName))
            return new AuthResult { Success = false, ErrorMessage = "Nombre y apellido son obligatorios" };
        if (string.IsNullOrWhiteSpace(email))
            return new AuthResult { Success = false, ErrorMessage = "El correo es obligatorio" };
        if (password.Length < 6)
            return new AuthResult { Success = false, ErrorMessage = "La contraseña debe tener al menos 6 caracteres" };

        try
        {
            var req = new RegisterRequest(firstName, lastName, email, password);
            var response = await _http.PostAsJsonAsync($"{ServerBase}/auth/register", req);
            var body = await response.Content.ReadAsStringAsync();

            if (response.IsSuccessStatusCode)
            {
                var token = JsonSerializer.Deserialize<TokenResponse>(body, _jOpt);
                if (token != null)
                {
                    ApplyToken(token);
                    PersistSession();
                    return new AuthResult { Success = true };
                }
            }

            return new AuthResult { Success = false, ErrorMessage = TryParseError(body) };
        }
        catch (Exception ex)
        {
            return new AuthResult { Success = false, ErrorMessage = $"Error: {ex.Message}" };
        }
    }

    // ── SESSION PERSISTENCE ────────────────────────────────────────────────

    public void RestoreSession()
    {
        var s = AppSettings.Instance;
        if (!string.IsNullOrEmpty(s.AuthToken))
        {
            Token        = s.AuthToken;
            UserId       = s.UserId;
            IsAdmin      = s.IsAdmin;
            FirstName    = s.UserFirstName;
            LastName     = s.UserLastName;
            Email        = s.UserEmail;
            LicenseType  = s.LicenseType;
            LicenseActive = s.LicenseActive;
        }
    }

    public void Logout()
    {
        Token        = "";
        UserId       = 0;
        IsAdmin      = false;
        FirstName    = "";
        LastName     = "";
        Email        = "";
        LicenseType  = "free";
        LicenseActive = false;

        var s = AppSettings.Instance;
        s.AuthToken   = "";
        s.UserId      = 0;
        s.IsAdmin     = false;
        s.UserFirstName = "";
        s.UserLastName  = "";
        s.UserEmail     = "";
        s.LicenseType   = "free";
        s.LicenseActive = false;
        s.Save();
    }

    public HttpClient GetAuthorizedClient()
    {
        _http.DefaultRequestHeaders.Remove("Authorization");
        if (!string.IsNullOrEmpty(Token))
            _http.DefaultRequestHeaders.Add("Authorization", $"Bearer {Token}");
        return _http;
    }

    // ── HELPERS ────────────────────────────────────────────────────────────

    private void ApplyToken(TokenResponse t)
    {
        Token        = t.AccessToken;
        UserId       = t.UserId;
        IsAdmin      = t.IsAdmin;
        FirstName    = t.FirstName;
        LastName     = t.LastName;
        Email        = t.Email;
        LicenseType  = t.LicenseType;
        LicenseActive = t.LicenseActive;
    }

    private void PersistSession()
    {
        var s = AppSettings.Instance;
        s.AuthToken     = Token;
        s.UserId        = UserId;
        s.IsAdmin       = IsAdmin;
        s.UserFirstName = FirstName;
        s.UserLastName  = LastName;
        s.UserEmail     = Email;
        s.LicenseType   = LicenseType;
        s.LicenseActive = LicenseActive;
        s.Save();
    }

    private static string TryParseError(string body)
    {
        try
        {
            var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("detail", out var d))
                return d.GetString() ?? "Error desconocido";
        }
        catch { }
        return "Error desconocido del servidor";
    }
}
