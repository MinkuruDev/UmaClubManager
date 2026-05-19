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
await sleep(6000)
button = document.querySelector('.save-button.expanded')
if (button.title.includes('.csv')) {
    button.click()
}
