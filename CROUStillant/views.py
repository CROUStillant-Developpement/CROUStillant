import discord


class WorkerView(discord.ui.LayoutView):
    def __init__(self, content: str, stats: str, thumbnail_url: str, banner_url: str, footer_text: str) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Container(
                discord.ui.Section(
                    content,
                    accessory=discord.ui.Thumbnail(media=thumbnail_url)
                ),
                discord.ui.TextDisplay(
                    stats,
                ),
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(media=banner_url)
                ),
                discord.ui.TextDisplay(content=f"-# *{footer_text}*")
            )
        )


class ErrorView(discord.ui.LayoutView):
    def __init__(self, content: str, thumbnail_url: str, banner_url: str, footer_text: str) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Container(
                discord.ui.Section(
                    content,
                    accessory=discord.ui.Thumbnail(media=thumbnail_url)
                ),
                discord.ui.MediaGallery(
                    discord.MediaGalleryItem(media=banner_url)
                ),
                discord.ui.TextDisplay(content=f"-# *{footer_text}*")
            )
        )
