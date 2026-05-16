# LinkedIn Automation for JARVIS

This guide explains how to use JARVIS's LinkedIn automation features to create, generate, and post content directly from your voice commands.

## Features

- **Voice-Controlled LinkedIn Posts**: Say commands to post on LinkedIn
- **AI-Generated Content**: Automatically generate LinkedIn posts using Groq AI
- **Scheduled Posts**: Schedule posts for later publication
- **Image Support**: Attach images to your posts
- **Tone & Length Control**: Customize content tone (professional/casual/inspirational) and length (short/medium/long)

## Setup

### 1. Install Dependencies

```bash
npm install
```

This will install Puppeteer and all other required dependencies.

### 2. Configure Environment Variables

Create a `.env` file in the root directory (copy from `.env.example`):

```env
# LinkedIn Credentials (Optional - can be entered via prompt)
LINKEDIN_EMAIL=your_email@example.com
LINKEDIN_PASSWORD=your_password

# AI API Keys (Required for content generation)
GROQ_API_KEY=gsk_your_key
GEMINI_API_KEY=AIzaSy_your_key
OPENROUTER_API_KEY=sk-or-v1_your_key
```

### 3. Start JARVIS

```bash
npm start
```

## Voice Commands

### Login to LinkedIn

```
"LinkedIn login"
"Connect LinkedIn"
"Login to LinkedIn"
```

JARVIS will prompt you for your LinkedIn email and password.

### Post Content

```
"Post on LinkedIn"
"Create LinkedIn post"
"Share on LinkedIn"
```

You'll be prompted to enter the content you want to post.

### Generate Content

```
"Generate LinkedIn content"
"Create LinkedIn content"
"Write LinkedIn post"
```

JARVIS will ask you for:
- **Topic**: What you want to write about
- **Tone**: professional, casual, or inspirational
- **Length**: short (50-100 words), medium (100-200 words), or long (200-300 words)

The AI will generate content, and you can choose to post it immediately.

### Schedule a Post

```
"Schedule LinkedIn post"
"Schedule post"
```

You'll be prompted for:
- **Content**: What to post
- **Date & Time**: When to post (format: YYYY-MM-DD HH:MM)

### Close LinkedIn Session

```
"Close LinkedIn"
"Logout LinkedIn"
"Disconnect LinkedIn"
```

## How It Works

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    JARVIS HUD (Electron)                    │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Renderer (renderer.js)                              │  │
│  │  - Voice input processing                            │  │
│  │  - LinkedIn command handlers                         │  │
│  │  - UI updates                                        │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Main Process (main.js)                              │  │
│  │  - IPC handlers for LinkedIn operations              │  │
│  │  - AI content generation (Groq)                      │  │
│  │  - LinkedIn automation coordination                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LinkedIn Automation Module (linkedin-automation.js) │  │
│  │  - Browser automation (Puppeteer)                    │  │
│  │  - LinkedIn login                                    │  │
│  │  - Post creation & publishing                        │  │
│  │  - Image upload                                      │  │
│  │  - Post scheduling                                   │  │
│  └──────────────────────────────────────────────────────┘  │
│                           ↓                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  External Services                                   │  │
│  │  - LinkedIn.com (browser automation)                 │  │
│  │  - Groq API (content generation)                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Workflow: Voice Command → LinkedIn Post

1. **Voice Input**: You speak a LinkedIn command
2. **STT Processing**: JARVIS converts speech to text
3. **Command Recognition**: Renderer identifies LinkedIn command
4. **Handler Execution**: Appropriate LinkedIn handler is called
5. **User Interaction**: Prompts for content/topic/schedule
6. **AI Generation** (if needed): Groq generates content
7. **Browser Automation**: Puppeteer logs in and posts
8. **Confirmation**: JARVIS confirms the action via voice

## Example Workflows

### Workflow 1: Quick Post

```
You: "Post on LinkedIn"
JARVIS: "What would you like to post on LinkedIn?"
You: [Enter content in prompt]
JARVIS: "Posting to LinkedIn, sir..."
[Browser opens, logs in, posts content]
JARVIS: "Post published successfully, sir!"
```

### Workflow 2: AI-Generated Post

```
You: "Generate LinkedIn content"
JARVIS: "What topic would you like me to write about?"
You: [Enter topic, e.g., "AI in web development"]
JARVIS: "What tone? (professional/casual/inspirational)"
You: [Select tone]
JARVIS: "What length? (short/medium/long)"
You: [Select length]
[AI generates content]
JARVIS: "I've generated LinkedIn content for you, sir. Would you like me to post it?"
You: [Confirm]
JARVIS: "Content posted successfully, sir!"
```

### Workflow 3: Scheduled Post

```
You: "Schedule LinkedIn post"
JARVIS: "What content would you like to schedule?"
You: [Enter content]
JARVIS: "When should this be posted? (YYYY-MM-DD HH:MM)"
You: [Enter date/time, e.g., "2024-12-25 09:00"]
JARVIS: "Post scheduled for 2024-12-25 09:00, sir!"
```

## API Reference

### IPC Handlers (main.js)

#### `linkedin-init`
Initialize LinkedIn automation with credentials.

```javascript
window.assistant.linkedInInit({ email, password })
// Returns: { success: boolean, message: string, error?: string }
```

#### `linkedin-generate-content`
Generate LinkedIn post content using AI.

```javascript
window.assistant.linkedInGenerateContent({ 
  topic: string, 
  tone?: "professional" | "casual" | "inspirational",
  length?: "short" | "medium" | "long"
})
// Returns: { success: boolean, content: string, error?: string }
```

#### `linkedin-post`
Create and post to LinkedIn.

```javascript
window.assistant.linkedInPost({ 
  content: string,
  imageUrl?: string,
  schedule?: boolean,
  scheduleTime?: ISO8601 timestamp
})
// Returns: { success: boolean, message: string, error?: string }
```

#### `linkedin-close`
Close LinkedIn browser session.

```javascript
window.assistant.linkedInClose()
// Returns: { success: boolean, message: string, error?: string }
```

#### `linkedin-auto-post`
Full workflow: Generate content and post to LinkedIn.

```javascript
window.assistant.linkedInAutoPost({ 
  topic: string,
  tone?: string,
  length?: string,
  imageUrl?: string,
  schedule?: boolean,
  scheduleTime?: ISO8601 timestamp
})
// Returns: { success: boolean, message: string, content: string, scheduled: boolean, error?: string }
```

## Troubleshooting

### Issue: "LinkedIn login failed"

**Solution**: 
- Verify your email and password are correct
- Check if LinkedIn has enabled 2FA (two-factor authentication)
- Try logging in manually first to ensure your account is accessible

### Issue: "Puppeteer browser won't open"

**Solution**:
- Ensure Puppeteer is installed: `npm install puppeteer`
- On Linux, install required dependencies: `sudo apt-get install libgconf-2-4`
- Try running with `headless: false` to see what's happening

### Issue: "Post button not found"

**Solution**:
- LinkedIn's UI may have changed
- Update the selectors in `linkedin-automation.js`
- Check browser console for element selectors

### Issue: "Content generation is slow"

**Solution**:
- Groq API may be rate-limited
- Check your API key quota
- Try using a shorter content length

## Advanced Usage

### Custom Content Generation

Modify the prompt in `linkedInGenerateContent()` in `main.js`:

```javascript
const prompt = `Generate a compelling LinkedIn post about "${topic}" in a ${tone} tone...`;
```

### Image Upload

To attach images to posts:

```javascript
const result = await window.assistant.linkedInPost({ 
  content: "Check out this image!",
  imageUrl: "https://example.com/image.jpg"
});
```

### Batch Posting

Create multiple posts programmatically:

```javascript
const topics = ["AI", "Web Dev", "JavaScript"];
for (const topic of topics) {
  const result = await window.assistant.linkedInAutoPost({ topic });
  console.log(`Posted about ${topic}`);
}
```

## Security Considerations

⚠️ **Important**: 

- **Never hardcode credentials** in your code
- Use environment variables or secure prompts
- LinkedIn may detect automated posting and require verification
- Consider using LinkedIn's official API for production use
- Be respectful of LinkedIn's terms of service

## Limitations

- LinkedIn may block automated posting if detected
- Browser automation is slower than API-based solutions
- Requires manual credential entry (no OAuth yet)
- Image upload may fail on some network configurations
- Scheduling is limited to LinkedIn's native scheduling capabilities

## Future Enhancements

- [ ] OAuth authentication (no password storage)
- [ ] LinkedIn API integration (faster, more reliable)
- [ ] Multi-account support
- [ ] Analytics integration (track post performance)
- [ ] Content templates
- [ ] Hashtag suggestions
- [ ] Best time to post recommendations
- [ ] Batch scheduling

## Support

For issues or feature requests, please check:
- LinkedIn's terms of service
- Puppeteer documentation: https://pptr.dev
- Groq API docs: https://console.groq.com/docs

---

**Built with ❤️ for JARVIS AI Assistant**
