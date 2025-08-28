"""Main CLI interface for the football news bot."""

import typer
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from app.config import settings
from app.utils.logging import setup_logging, get_logger
from app.pipeline import pipeline
from app.publisher.x_client import x_client
from app.utils.dedupe import deduplicator

# Initialize Typer app
app = typer.Typer(
    name="futbot",
    help="Otomatik futbol haber botu - Türkçe futbol haberlerini toplar ve X'te paylaşır",
    rich_markup_mode="rich"
)

console = Console()
logger = get_logger(__name__)


@app.command()
def ingest(
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Sadece göster, işleme"),
    max_items: int = typer.Option(20, "--max", help="Maksimum haber sayısı")
):
    """Haber kaynaklarından haberleri topla ve önbelleğe yaz."""
    console.print("[bold blue]Haber toplama başlıyor...[/bold blue]")
    
    try:
        items = pipeline.ingest_news()
        
        if not items:
            console.print("[yellow]Hiç haber bulunamadı[/yellow]")
            return
        
        # Show results in table
        table = Table(title=f"Toplanan Haberler ({len(items)})")
        table.add_column("Başlık", style="cyan", no_wrap=False, max_width=50)
        table.add_column("Kaynak", style="magenta")
        table.add_column("Tarih", style="green")
        
        for item in items[:max_items]:
            date_str = item.published_at.strftime("%H:%M") if item.published_at else "Bilinmiyor"
            table.add_row(
                item.title[:47] + "..." if len(item.title) > 50 else item.title,
                item.source,
                date_str
            )
        
        console.print(table)
        
        if dry_run:
            console.print("\n[yellow]DRY RUN: Hiçbir şey kaydedilmedi[/yellow]")
        else:
            console.print(f"\n[green]✓ {len(items)} haber başarıyla toplandı[/green]")
            
    except Exception as e:
        console.print(f"[red]Hata: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def run_once(
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Sadece göster, yayınlama"),
    max_items: int = typer.Option(5, "--max", help="Maksimum işlenecek haber sayısı"),
    post: bool = typer.Option(False, "--post", help="X'te yayınla")
):
    """Tek tur pipeline çalıştır - haberleri topla, işle ve yayınla."""
    actual_dry_run = dry_run and not post
    
    if not actual_dry_run:
        console.print("[bold red]CANLI MOD: Haberler X'te yayınlanacak![/bold red]")
        if not typer.confirm("Devam etmek istiyor musunuz?"):
            raise typer.Exit()
    
    console.print("[bold blue]Pipeline başlıyor...[/bold blue]")
    
    try:
        processed_items = pipeline.run_pipeline(dry_run=actual_dry_run, max_items=max_items)
        
        if not processed_items:
            console.print("[yellow]İşlenecek haber bulunamadı[/yellow]")
            return
        
        # Show results
        table = Table(title=f"İşlenen Haberler ({len(processed_items)})")
        table.add_column("Başlık", style="cyan", max_width=40)
        table.add_column("Tür", style="magenta")
        table.add_column("Güven", style="green")
        table.add_column("Durum", style="yellow")
        
        for item in processed_items:
            news_type = item.news_type.value if item.news_type else "bilinmiyor"
            confidence = f"{item.confidence:.2f}" if item.confidence else "0.00"
            
            if actual_dry_run:
                status = "DRY RUN"
            elif item.post_result:
                status = "✓ Yayınlandı"
            else:
                status = "✗ Başarısız"
            
            table.add_row(
                item.original.title[:37] + "..." if len(item.original.title) > 40 else item.original.title,
                news_type.upper(),
                confidence,
                status
            )
        
        console.print(table)
        
        # Show sample posts
        if processed_items:
            console.print("\n[bold]Örnek Gönderiler:[/bold]")
            for i, item in enumerate(processed_items[:3]):
                panel = Panel(
                    item.formatted_text,
                    title=f"Gönderi {i+1} ({item.news_type.value if item.news_type else 'bilinmiyor'})",
                    border_style="blue"
                )
                console.print(panel)
        
        if actual_dry_run:
            console.print("\n[yellow]DRY RUN: Hiçbir şey yayınlanmadı[/yellow]")
        else:
            published_count = sum(1 for item in processed_items if item.post_result)
            console.print(f"\n[green]✓ {published_count} haber başarıyla yayınlandı[/green]")
            
    except Exception as e:
        console.print(f"[red]Pipeline hatası: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def backfill(
    hours: int = typer.Option(24, "--hours", help="Son X saatteki haberleri işle"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Sadece göster, yayınlama")
):
    """Son X saatteki haberleri geri doldur."""
    console.print(f"[bold blue]Son {hours} saatteki haberler işleniyor...[/bold blue]")
    
    try:
        # This would need additional implementation to filter by time range
        processed_items = pipeline.run_pipeline(dry_run=dry_run, max_items=20)
        
        console.print(f"[green]✓ {len(processed_items)} haber işlendi[/green]")
        
    except Exception as e:
        console.print(f"[red]Backfill hatası: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def test_connection():
    """X/Twitter API bağlantısını test et."""
    console.print("[bold blue]X/Twitter bağlantısı test ediliyor...[/bold blue]")
    
    try:
        if x_client.test_connection():
            console.print("[green]✓ X/Twitter bağlantısı başarılı[/green]")
        else:
            console.print("[red]✗ X/Twitter bağlantısı başarısız[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]Bağlantı hatası: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def status():
    """Bot durumunu göster."""
    console.print("[bold blue]Bot Durumu[/bold blue]")
    
    # Configuration status
    config_table = Table(title="Konfigürasyon")
    config_table.add_column("Ayar", style="cyan")
    config_table.add_column("Değer", style="green")
    
    config_table.add_row("RSS Kaynakları", str(len(settings.config.sources.rss)))
    config_table.add_row("Web Siteleri", str(len(settings.config.sources.sites)))
    config_table.add_row("Günlük Limit", str(settings.config.rate_limits.daily_post_cap))
    config_table.add_row("Dakika Aralığı", str(settings.config.rate_limits.min_minutes_between_posts))
    config_table.add_row("X Kimlik Bilgileri", "✓" if settings.has_x_credentials() else "✗")
    
    console.print(config_table)
    
    # Recent posts
    try:
        recent_posts = deduplicator.get_recent_posts(hours=24)
        if recent_posts:
            posts_table = Table(title="Son 24 Saatteki Gönderiler")
            posts_table.add_column("Başlık", style="cyan", max_width=50)
            posts_table.add_column("Kaynak", style="magenta")
            posts_table.add_column("Zaman", style="green")
            
            for post in recent_posts[:10]:
                posts_table.add_row(
                    post['title'][:47] + "..." if len(post['title']) > 50 else post['title'],
                    post['source'],
                    post['posted_at'][:16]  # YYYY-MM-DD HH:MM
                )
            
            console.print(posts_table)
        else:
            console.print("[yellow]Son 24 saatte gönderi yok[/yellow]")
            
    except Exception as e:
        console.print(f"[red]Durum bilgisi alınamadı: {e}[/red]")


@app.command()
def cleanup(
    days: int = typer.Option(30, "--days", help="X günden eski kayıtları temizle")
):
    """Eski kayıtları temizle."""
    console.print(f"[bold blue]{days} günden eski kayıtlar temizleniyor...[/bold blue]")
    
    try:
        deduplicator.cleanup_old_entries(days)
        console.print("[green]✓ Temizlik tamamlandı[/green]")
        
    except Exception as e:
        console.print(f"[red]Temizlik hatası: {e}[/red]")
        raise typer.Exit(1)


@app.callback()
def main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Detaylı log"),
    log_file: Optional[str] = typer.Option(None, "--log-file", help="Log dosyası")
):
    """Futbol Haber Botu - Otomatik Türkçe futbol haberleri."""
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level, log_file)
    
    # Show welcome message
    if verbose:
        console.print(Panel.fit(
            "[bold blue]Futbol Haber Botu[/bold blue]\n"
            "Otomatik Türkçe futbol haberleri için X/Twitter botu",
            border_style="blue"
        ))


if __name__ == "__main__":
    app()
