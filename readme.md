This is a high-level analyzer (HLA) for decoding SD and MMC comminication with a Saleae logic analyzer.

### Setup

To use this extension, do the following:

* Install Saleae Logic 2.
  * As of the time of writing, the latest version was v2.2.17.

* Install this extension in Logic 2.
  * Downloading the "hla" directory to your computer.
  * In the "Extensions" tab, select "Create Extension" and select "Load existing extension."
  * Select the "sdmmc_from_spi.json" file on your computer.

* Create an SPI analyzer with the following inputs:
  * MOSI mapped to SDIO_CMD
  * MISO unmapped
  * Clock mapped to SDIO/CK
  * Enable unmapped (important)
  * MSB first
  * 8 bits per transfer
  * CPOL = 0
  * CPHA = 0

* Create an SDMMC (from SPI) analyzer with the above SPI analyzer as the input.

### Example

The SPI analyzer should be outputting results similiar to the following:

![](.readme_images/spi_output.png)

Because of the way the analyzer works, you may need to trim your results such that SPI_SCK is low at the beginning of the capture.

When there is activity on the CMD line, the analyzer will output info about it.  The following shows the identification handshake between the host and the device.

![](.readme_images/sdmmc_identification_example.png)

### Notes

This extension is not compatible with Saleae Logic 1.x.

The SD and MMC protocols are very similar.  This analyzer is applicable to both.

The value of the CRC7 in commands and reponses is not checked.

The data lines are not decoded.
