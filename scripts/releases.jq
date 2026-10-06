# GitHub's release list, trimmed to what templates/releases.html and the front page read.
[.[] | select(.draft | not) | {
  tag: .tag_name, name: .name, published: .published_at, url: .html_url,
  prerelease: .prerelease, body: .body,
  assets: [.assets[] | {name: .name, url: .browser_download_url, size: .size}]
}]
