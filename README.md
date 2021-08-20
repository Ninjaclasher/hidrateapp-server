# HidrateSpark Server

This is an **unofficial** server for the HidrateSpark smart water bottle, as I got sick of the VPN block and enormous amounts of data collection.

Provided are two servers:
 1. `mitm` - a lightweight server that strips sensitive information from your requests, and forwards these requests to upstream. An optional flag can log all these requests in case you wish to have a copy of your data. Requires a residential IP to not be blocked by upstream.
 2. `full` - a full server that is a drop-in replacement for upstream. Requires some more work to set up a proper database.

See the individual READMEs and [my blog post](https://evanzhang.ca/blog/smart-water-bottle-reversing/) for more details on the required set up.
