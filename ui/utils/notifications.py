import streamlit as st
import streamlit.components.v1 as components

def play_success_sound():
    """
    Toca um aviso sonoro de sucesso (acorde agradável) usando a Web Audio API.
    Isso funciona diretamente no navegador sem necessidade de arquivos externos.
    """
    chime_js = """
    <script>
    (function() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            if (!AudioContext) return;
            
            const context = new AudioContext();
            const now = context.currentTime;
            
            // Acorde de Dó Maior (C5, E5, G5, C6) para um som de 'sucesso'
            const notes = [523.25, 659.25, 783.99, 1046.50]; 
            
            notes.forEach((freq, i) => {
                const osc = context.createOscillator();
                const gain = context.createGain();
                
                osc.type = 'sine';
                osc.frequency.setValueAtTime(freq, now + (i * 0.07));
                
                // Ataque rápido e decaimento suave
                gain.gain.setValueAtTime(0, now + (i * 0.07));
                gain.gain.linearRampToValueAtTime(0.1, now + (i * 0.07) + 0.01);
                gain.gain.exponentialRampToValueAtTime(0.0001, now + (i * 0.07) + 1.0);
                
                osc.connect(gain);
                gain.connect(context.destination);
                
                osc.start(now + (i * 0.07));
                osc.stop(now + (i * 0.07) + 1.0);
            });
        } catch (e) { 
            console.warn("Audio notification failed:", e); 
        }
    })();
    </script>
    """
    # Injeta o script em um componente oculto
    st.iframe(srcdoc=chime_js, height=0, width=0)

def notify_completion(message="Processamento concluído com sucesso!"):
    """
    Exibe uma notificação visual (toast) e emite um aviso sonoro.
    """
    st.toast(message, icon="✅")
    play_success_sound()
