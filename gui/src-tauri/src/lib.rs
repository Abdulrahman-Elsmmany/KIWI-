use serde::{Deserialize, Serialize};
use tauri::command;

#[derive(Debug, Serialize, Deserialize)]
struct Voice {
    name: String,
    language_code: String,
    ssml_gender: String,
    display_name: Option<String>,
}

#[derive(Debug, Serialize, Deserialize)]
struct VoicesResponse {
    voices: Vec<Voice>,
    language_code: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct TTSRequest {
    text: String,
    voice: String,
    format: String,
    language: String,
}

#[derive(Debug, Serialize, Deserialize)]
struct ConversionResult {
    success: bool,
    output_path: Option<String>,
    error: Option<String>,
    file_size: Option<String>,
    processing_time: Option<String>,
    download_url: Option<String>,
}

const API_BASE_URL: &str = "http://127.0.0.1:8000";

#[command]
async fn get_available_voices(language_code: String) -> Result<Vec<Voice>, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/voices/{}", API_BASE_URL, language_code);
    
    match client.get(&url).send().await {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<VoicesResponse>().await {
                    Ok(voices_response) => Ok(voices_response.voices),
                    Err(e) => Err(format!("Failed to parse voices response: {}", e)),
                }
            } else {
                // Fallback voices when API server is not running
                let chirp_voices = vec![
                    "Charon", "Kore", "Zephyr", "Achernar", "Pulcherrima", "Leda", 
                    "Aoede", "Callirrhoe", "Despina", "Enceladus", "Puck", "Umbriel"
                ];
                
                let voices: Vec<Voice> = chirp_voices.iter().map(|&voice_name| {
                    let gender = if ["Charon", "Kore", "Leda", "Aoede", "Callirrhoe", "Pulcherrima", "Despina"].contains(&voice_name) {
                        "FEMALE"
                    } else {
                        "MALE"
                    };
                    
                    Voice {
                        name: format!("{}-Chirp3-HD-{}", language_code, voice_name),
                        language_code: language_code.clone(),
                        ssml_gender: gender.to_string(),
                        display_name: Some(format!("{} (HD)", voice_name)),
                    }
                }).collect();
                
                Ok(voices)
            }
        }
        Err(e) => {
            // Network error - return fallback voices
            let chirp_voices = vec![
                "Charon", "Kore", "Zephyr", "Achernar", "Pulcherrima", "Leda", 
                "Aoede", "Callirrhoe", "Despina", "Enceladus", "Puck", "Umbriel"
            ];
            
            let voices: Vec<Voice> = chirp_voices.iter().map(|&voice_name| {
                let gender = if ["Charon", "Kore", "Leda", "Aoede", "Callirrhoe", "Pulcherrima", "Despina"].contains(&voice_name) {
                    "FEMALE"
                } else {
                    "MALE"
                };
                
                Voice {
                    name: format!("{}-Chirp3-HD-{}", language_code, voice_name),
                    language_code: language_code.clone(),
                    ssml_gender: gender.to_string(),
                    display_name: Some(format!("{} (HD)", voice_name)),
                }
            }).collect();
            
            println!("API server not available ({}), using fallback voices", e);
            Ok(voices)
        }
    }
}

#[command]
async fn convert_text_to_speech(
    text: String,
    voice: String,
    format: String,
    output_path: String,
    verbose: bool,
) -> Result<ConversionResult, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/synthesize", API_BASE_URL);
    
    let request_body = TTSRequest {
        text,
        voice,
        format: format.clone(),
        language: "en-US".to_string(),
    };
    
    if verbose {
        println!("Sending TTS request to API server...");
    }
    
    match client.post(&url).json(&request_body).send().await {
        Ok(response) => {
            if response.status().is_success() {
                match response.json::<ConversionResult>().await {
                    Ok(mut result) => {
                        // Download the file if API returned a download URL
                        if result.success && result.download_url.is_some() {
                            let download_url = result.download_url.as_ref().unwrap();
                            let full_download_url = format!("{}{}", API_BASE_URL, download_url);
                            
                            match client.get(&full_download_url).send().await {
                                Ok(download_response) => {
                                    if download_response.status().is_success() {
                                        match download_response.bytes().await {
                                            Ok(bytes) => {
                                                match std::fs::write(&output_path, bytes) {
                                                    Ok(_) => {
                                                        result.output_path = Some(output_path);
                                                        if verbose {
                                                            println!("Audio file downloaded successfully");
                                                        }
                                                        Ok(result)
                                                    }
                                                    Err(e) => {
                                                        result.success = false;
                                                        result.error = Some(format!("Failed to save audio file: {}", e));
                                                        Ok(result)
                                                    }
                                                }
                                            }
                                            Err(e) => {
                                                result.success = false;
                                                result.error = Some(format!("Failed to read audio data: {}", e));
                                                Ok(result)
                                            }
                                        }
                                    } else {
                                        result.success = false;
                                        result.error = Some(format!("Download failed with status: {}", download_response.status()));
                                        Ok(result)
                                    }
                                }
                                Err(e) => {
                                    result.success = false;
                                    result.error = Some(format!("Failed to download audio file: {}", e));
                                    Ok(result)
                                }
                            }
                        } else {
                            Ok(result)
                        }
                    }
                    Err(e) => Err(format!("Failed to parse TTS response: {}", e)),
                }
            } else {
                let status = response.status();
                match response.text().await {
                    Ok(error_text) => Ok(ConversionResult {
                        success: false,
                        output_path: None,
                        error: Some(format!("API error: {}", error_text)),
                        file_size: None,
                        processing_time: None,
                        download_url: None,
                    }),
                    Err(_) => Ok(ConversionResult {
                        success: false,
                        output_path: None,
                        error: Some(format!("API returned status: {}", status)),
                        file_size: None,
                        processing_time: None,
                        download_url: None,
                    })
                }
            }
        }
        Err(e) => Ok(ConversionResult {
            success: false,
            output_path: None,
            error: Some(format!("Failed to connect to API server: {}. Make sure the server is running with 'uv run kiwi server'", e)),
            file_size: None,
            processing_time: None,
            download_url: None,
        })
    }
}

#[command]
async fn open_file_path(path: String) -> Result<(), String> {
    #[cfg(target_os = "windows")]
    {
        std::process::Command::new("cmd")
            .args(["/C", "start", "", &path])
            .output()
            .map_err(|e| format!("Failed to open file: {}", e))?;
    }
    
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(&path)
            .output()
            .map_err(|e| format!("Failed to open file: {}", e))?;
    }
    
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(&path)
            .output()
            .map_err(|e| format!("Failed to open file: {}", e))?;
    }

    Ok(())
}

#[command]
async fn open_folder_path(path: String) -> Result<(), String> {
    let file_path = std::path::Path::new(&path);
    
    // Check if the path exists
    if !file_path.exists() {
        return Err(format!("File does not exist: {}", path));
    }
    
    let folder_path = if file_path.is_file() {
        // If it's a file, get the parent directory
        file_path.parent()
            .ok_or("Cannot determine parent directory")?
            .to_string_lossy()
            .to_string()
    } else {
        // If it's already a directory, use it directly
        path.clone()
    };

    #[cfg(target_os = "windows")]
    {
        // On Windows, use explorer with /select to highlight the file
        if file_path.is_file() {
            std::process::Command::new("explorer")
                .args(["/select,", &path])
                .output()
                .map_err(|e| format!("Failed to open folder: {}", e))?;
        } else {
            std::process::Command::new("explorer")
                .arg(&folder_path)
                .output()
                .map_err(|e| format!("Failed to open folder: {}", e))?;
        }
    }
    
    #[cfg(target_os = "macos")]
    {
        if file_path.is_file() {
            // On macOS, use -R flag to reveal the file in Finder
            std::process::Command::new("open")
                .args(["-R", &path])
                .output()
                .map_err(|e| format!("Failed to open folder: {}", e))?;
        } else {
            std::process::Command::new("open")
                .arg(&folder_path)
                .output()
                .map_err(|e| format!("Failed to open folder: {}", e))?;
        }
    }
    
    #[cfg(target_os = "linux")]
    {
        // On Linux, try different file managers
        let commands = ["nautilus", "dolphin", "thunar", "pcmanfm"];
        let mut success = false;
        
        for cmd in &commands {
            if file_path.is_file() {
                // Try to select the file if supported
                match std::process::Command::new(cmd)
                    .arg("--select")
                    .arg(&path)
                    .output() 
                {
                    Ok(_) => {
                        success = true;
                        break;
                    }
                    Err(_) => continue,
                }
            }
        }
        
        if !success {
            // Fallback to opening the folder
            std::process::Command::new("xdg-open")
                .arg(&folder_path)
                .output()
                .map_err(|e| format!("Failed to open folder: {}", e))?;
        }
    }

    Ok(())
}

#[command]
async fn select_output_folder() -> Result<Option<String>, String> {
    use std::process::Command;
    
    #[cfg(target_os = "windows")]
    {
        // PowerShell folder picker dialog
        let output = Command::new("powershell")
            .args([
                "-Command", 
                "Add-Type -AssemblyName System.Windows.Forms; $f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = 'Select output folder for audio files'; $f.SelectedPath = [Environment]::GetFolderPath('MyDocuments'); if ($f.ShowDialog() -eq 'OK') { $f.SelectedPath } else { '' }"
            ])
            .output()
            .map_err(|e| format!("Failed to open folder dialog: {}", e))?;
        
        let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if path.is_empty() {
            Ok(None)
        } else {
            Ok(Some(path))
        }
    }
    
    #[cfg(target_os = "macos")]
    {
        // AppleScript folder picker dialog
        let output = Command::new("osascript")
            .args([
                "-e", 
                "set chosenFolder to choose folder with prompt \"Select output folder for audio files:\" default location (path to documents folder)"
            ])
            .output()
            .map_err(|e| format!("Failed to open folder dialog: {}", e))?;
        
        if output.status.success() {
            let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
            // Convert AppleScript path format to Unix path
            let unix_path = path.replace(":", "/").replace("Macintosh HD", "");
            Ok(Some(unix_path))
        } else {
            Ok(None)
        }
    }
    
    #[cfg(target_os = "linux")]
    {
        // Try various Linux folder dialogs
        let commands = [
            ("zenity", vec!["--file-selection", "--directory", "--title=Select output folder for audio files"]),
            ("kdialog", vec!["--getexistingdirectory", ".", "--title", "Select output folder for audio files"]),
            ("yad", vec!["--file-selection", "--directory", "--title=Select output folder for audio files"]),
        ];
        
        for (cmd, args) in &commands {
            match Command::new(cmd).args(args).output() {
                Ok(output) if output.status.success() => {
                    let path = String::from_utf8_lossy(&output.stdout).trim().to_string();
                    if !path.is_empty() {
                        return Ok(Some(path));
                    }
                }
                _ => continue,
            }
        }
        
        // Fallback: return user's home directory
        if let Ok(home) = std::env::var("HOME") {
            Ok(Some(format!("{}/Downloads", home)))
        } else {
            Ok(Some("/tmp".to_string()))
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .invoke_handler(tauri::generate_handler![
            get_available_voices,
            convert_text_to_speech,
            open_file_path,
            open_folder_path,
            select_output_folder
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}