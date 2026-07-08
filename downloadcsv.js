// sleep function
const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

await sleep(3000);
// close popup when first visiting the page
buttons = document.querySelectorAll('.generic-button')
buttons.forEach(button => {
    if (button.textContent === 'Close') {
        button.click()
    }
})

// wait for the download button to appear and click it
let attempts = 10
let counter = 0
while (counter < attempts) {
    button = document.querySelector('.save-button.expanded')
    if (button && button.title.includes('.csv')) {
        button.click()
        break
    }
    await sleep(6000)
    counter++
}
